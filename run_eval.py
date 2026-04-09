import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runner.benchmark import run_benchmark, run_quality_samples, run_smoke
from runner.judge_api import run_judge_eval
from runner.launch import cleanup_service, launch_service
from runner.preflight import run_preflight
from runner.report import build_markdown, build_summary
from runner.utils import ensure_dir, load_json, make_run_id, write_json, write_text


def _resolve_eval_mode(eval_mode):
    if eval_mode not in ('quick', 'standard', 'deep'):
        return 'quick'
    return eval_mode


def _resolve_judge_mode(judge_mode):
    if judge_mode not in ('builtin', 'api'):
        return 'builtin'
    return judge_mode


def _quality_prompts_path(eval_mode):
    return ROOT / 'configs' / 'prompts' / 'quality_{}.jsonl'.format(eval_mode)


def _judge_prompt_path(eval_mode):
    return ROOT / 'prompts' / 'judge_{}.txt'.format(eval_mode)


def _print_final_brief(out_dir):
    brief_path = out_dir / 'final_brief.md'
    if not brief_path.exists():
        return
    print('\n===== FINAL BRIEF =====')
    print(brief_path.read_text(encoding='utf-8').strip())
    print('===== END FINAL BRIEF =====\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, help='镜像配置文件路径')
    parser.add_argument('--judge-api-base', default='', help='评测 API Base，例如 https://api.mooko.ai/v1')
    parser.add_argument('--judge-api-key', default='', help='评测 API Key')
    parser.add_argument('--judge-model', default='mooko/gpt-5.4', help='评测模型名，例如 mooko/gpt-5.4')
    parser.add_argument('--judge-timeout-sec', type=int, default=180, help='评测 API 超时时间')
    parser.add_argument('--judge-mode', default='builtin', help='评测模式：builtin / api')
    parser.add_argument('--eval-mode', default='quick', help='评测模式：quick / standard / deep')
    parser.add_argument('--keep-container', action='store_true', help='执行完成后不自动清理容器')
    args = parser.parse_args()

    eval_mode = _resolve_eval_mode(args.eval_mode)
    judge_mode = _resolve_judge_mode(args.judge_mode)
    config_path = (ROOT / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    config = load_json(config_path)
    run_id = make_run_id(config['name'] + '_' + eval_mode)
    out_dir = ensure_dir(ROOT / 'outputs' / run_id)

    quality_prompts_path = _quality_prompts_path(eval_mode)
    judge_prompt_path = _judge_prompt_path(eval_mode)
    reuse_existing_service = bool(config.get('reuse_existing_service', False))

    write_json(out_dir / 'meta.json', {
        'run_id': run_id,
        'config_path': str(config_path),
        'config': config,
        'eval_mode': eval_mode,
        'judge_mode': judge_mode,
        'judge_prompt_path': str(judge_prompt_path),
        'quality_prompts_path': str(quality_prompts_path),
        'reuse_existing_service': reuse_existing_service,
        'judge_api': {
            'api_base': args.judge_api_base,
            'model': args.judge_model,
            'timeout_sec': args.judge_timeout_sec,
        }
    })

    preflight = run_preflight(config)
    write_json(out_dir / 'preflight.json', preflight)
    if not preflight.get('passed'):
        print('[FAIL] preflight failed, see {}'.format(out_dir / 'preflight.json'))
        return 1

    if reuse_existing_service:
        launch = {
            'stage': 'launch',
            'timestamp': preflight.get('timestamp'),
            'passed': True,
            'command': None,
            'container_id': config.get('existing_container_name', ''),
            'stdout': '',
            'stderr': 'reuse_existing_service=true, skipped launch',
            'ready_check': {
                'ready': True,
                'url': config['base_url'] + config.get('healthcheck_path', '/v1/models'),
                'status_code': None,
                'body': 'reuse_existing_service=true, ready check deferred to smoke/benchmark stage',
            },
        }
    else:
        launch = launch_service(config)
    write_json(out_dir / 'launch.json', launch)
    if not launch.get('passed'):
        print('[FAIL] launch failed, see {}'.format(out_dir / 'launch.json'))
        return 1

    base_url = config['base_url'].rstrip('/') if reuse_existing_service else 'http://127.0.0.1:{}'.format(config.get('host_port', 18000))
    smoke = run_smoke(base_url, config['model_id'], str(ROOT / 'configs' / 'prompts' / 'smoke.jsonl'))
    write_json(out_dir / 'smoke.json', smoke)

    benchmark = run_benchmark(base_url, config['model_id'])
    write_json(out_dir / 'benchmark.json', benchmark)

    quality_samples = run_quality_samples(base_url, config['model_id'], str(quality_prompts_path))
    write_json(out_dir / 'quality_samples.json', quality_samples)

    if judge_mode == 'api' and (not args.judge_api_base or not args.judge_api_key):
        print('[FAIL] judge_mode=api 但缺少 judge-api-base 或 judge-api-key')
        return 1

    judge_eval = run_judge_eval(
        api_base=args.judge_api_base,
        api_key=args.judge_api_key,
        judge_model=args.judge_model,
        prompt_template_path=str(judge_prompt_path),
        eval_mode=eval_mode,
        base_url=base_url,
        model_id=config['model_id'],
        quality_prompts_path=str(quality_prompts_path),
        sampled_outputs=quality_samples.get('results', []),
        output_dir=str(out_dir),
        timeout_sec=args.judge_timeout_sec,
        judge_mode=judge_mode,
    )

    summary = build_summary(config, run_id, preflight, launch, smoke, benchmark, judge_eval)
    write_json(out_dir / 'summary.json', summary)

    report = build_markdown(summary, preflight, launch, smoke, benchmark, judge_eval)
    write_text(out_dir / 'report.md', report)

    if (not reuse_existing_service) and (not args.keep_container):
        cleanup = cleanup_service(config)
        write_json(out_dir / 'cleanup.json', cleanup)

    print('\n[DONE] run_id={}'.format(run_id))
    print('[DONE] outputs={}'.format(out_dir))
    _print_final_brief(out_dir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
