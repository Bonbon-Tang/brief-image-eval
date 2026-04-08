import json
import time
from pathlib import Path

import requests

from runner.utils import load_jsonl, utc_timestamp, write_json, write_text


def _normalize_result(data, raw_output=None):
    if not isinstance(data, dict):
        return {
            'judge_mode': 'api',
            'overall_status': 'FAIL',
            'summary': 'judge API 返回结果不是对象',
            'cases': [],
            'risks': ['judge API 返回结构异常'],
            'recommendations': ['检查 judge prompt 和模型输出'],
            'raw_output': raw_output,
        }
    data.setdefault('judge_mode', 'api')
    data.setdefault('overall_status', 'FAIL')
    data.setdefault('summary', '')
    data.setdefault('cases', [])
    data.setdefault('risks', [])
    data.setdefault('recommendations', [])
    if data['overall_status'] not in ('PASS', 'WARN', 'FAIL'):
        data['overall_status'] = 'FAIL'
    return data


def call_judge_api(api_base, api_key, model, prompt_text, timeout_sec=180, max_retries=2, retry_wait_sec=3):
    url = api_base.rstrip('/') + '/chat/completions'
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': '你是一个严谨的 LLM 服务质量评测器。输出必须是合法 JSON。'},
            {'role': 'user', 'content': prompt_text},
        ],
        'temperature': 0,
    }
    headers = {
        'Authorization': 'Bearer ' + api_key,
        'Content-Type': 'application/json',
    }

    last_result = None
    for attempt in range(max_retries + 1):
        start = time.time()
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout_sec)
            latency_ms = round((time.time() - start) * 1000, 2)
            text = resp.text
            raw = None
            try:
                raw = resp.json()
                text = raw['choices'][0]['message']['content']
            except Exception:
                raw = {'raw_text': resp.text}

            try:
                data = json.loads(text)
            except Exception:
                data = {
                    'judge_mode': 'api',
                    'overall_status': 'FAIL',
                    'summary': 'judge API 返回内容不是合法 JSON',
                    'cases': [],
                    'risks': ['judge API 输出格式异常'],
                    'recommendations': ['检查 judge model 提示词或返回格式'],
                    'raw_output': text,
                }

            last_result = {
                'timestamp': utc_timestamp(),
                'http_status': resp.status_code,
                'latency_ms': latency_ms,
                'attempt': attempt + 1,
                'raw_response': raw,
                'parsed_result': _normalize_result(data, raw_output=text),
            }
            if resp.status_code == 200:
                return last_result
        except Exception as e:
            last_result = {
                'timestamp': utc_timestamp(),
                'http_status': -1,
                'latency_ms': None,
                'attempt': attempt + 1,
                'raw_response': None,
                'parsed_result': {
                    'judge_mode': 'api',
                    'overall_status': 'FAIL',
                    'summary': 'judge API 调用异常: {}'.format(e),
                    'cases': [],
                    'risks': ['judge API 不可用'],
                    'recommendations': ['检查网络、API Base、API Key、模型名'],
                },
            }
        if attempt < max_retries:
            time.sleep(retry_wait_sec)
    return last_result


def build_judge_prompt(prompt_template_path, base_url, model_id, quality_prompts_path, sampled_outputs, eval_mode):
    template = Path(prompt_template_path).read_text(encoding='utf-8')
    cases = load_jsonl(quality_prompts_path)
    payload = {
        'eval_mode': eval_mode,
        'service_base_url': base_url,
        'tested_model_id': model_id,
        'quality_cases': cases,
        'model_outputs': sampled_outputs,
        'required_schema': {
            'overall_status': 'PASS|WARN|FAIL',
            'summary': 'string',
            'cases': [
                {
                    'id': 'string',
                    'category': 'string',
                    'prompt': 'string',
                    'response': 'string',
                    'latency_ms': 0,
                    'verdict': 'PASS|WARN|FAIL',
                    'notes': 'string'
                }
            ],
            'risks': ['string'],
            'recommendations': ['string']
        }
    }
    return template + '\n\n评测上下文：\n' + json.dumps(payload, ensure_ascii=False, indent=2)


def write_final_brief(output_dir, parsed):
    overall = parsed.get('overall_status', 'FAIL')
    summary = parsed.get('summary', '')
    risks = parsed.get('risks', [])[:3]
    recommendations = parsed.get('recommendations', [])[:3]

    lines = []
    lines.append('# 评测摘要')
    lines.append('')
    lines.append('结论：{}'.format(overall))
    lines.append('一句话：{}'.format(summary or '无'))
    lines.append('')
    if risks:
        lines.append('主要风险：')
        for item in risks:
            lines.append('- {}'.format(item))
        lines.append('')
    if recommendations:
        lines.append('建议下一步：')
        for item in recommendations:
            lines.append('- {}'.format(item))
        lines.append('')
    write_text(Path(output_dir) / 'final_brief.md', '\n'.join(lines))


def _build_builtin_case(row):
    if row.get('error'):
        return {
            'id': row.get('id', 'unknown'),
            'category': row.get('category', 'quality'),
            'prompt': row.get('prompt', ''),
            'response': '',
            'latency_ms': row.get('latency_ms', 0),
            'verdict': 'FAIL',
            'notes': '请求失败: {}'.format(row.get('error')),
        }

    text = (row.get('response_text') or '').strip()
    latency = row.get('latency_ms', 0)

    verdict = 'PASS'
    notes = []

    if not text:
        verdict = 'FAIL'
        notes.append('返回内容为空')
    elif len(text) < 10:
        verdict = 'WARN'
        notes.append('返回内容较短，可能信息不足')

    if latency and latency > 60000:
        verdict = 'WARN' if verdict == 'PASS' else verdict
        notes.append('单条响应耗时较高')

    if not notes:
        notes.append('响应正常，具备基本可读性')

    return {
        'id': row.get('id', 'unknown'),
        'category': row.get('category', 'quality'),
        'prompt': row.get('prompt', ''),
        'response': text[:1000],
        'latency_ms': latency,
        'verdict': verdict,
        'notes': '；'.join(notes),
    }


def run_builtin_judge_eval(eval_mode, base_url, model_id, sampled_outputs, output_dir):
    cases = [_build_builtin_case(row) for row in sampled_outputs]
    fail_count = sum(1 for c in cases if c['verdict'] == 'FAIL')
    warn_count = sum(1 for c in cases if c['verdict'] == 'WARN')
    pass_count = sum(1 for c in cases if c['verdict'] == 'PASS')

    if fail_count > 0:
        overall = 'FAIL'
        summary = '内置评测发现 {} 个失败样例，服务链路或输出质量存在明显问题。'.format(fail_count)
    elif warn_count > 0:
        overall = 'WARN'
        summary = '内置评测通过，但存在 {} 个告警样例，建议进一步人工复核。'.format(warn_count)
    else:
        overall = 'PASS'
        summary = '内置评测通过，样例输出整体正常，可继续后续验证。'

    risks = []
    recommendations = []

    if fail_count > 0:
        risks.append('存在失败样例，说明服务链路或模型响应仍不稳定')
        recommendations.append('优先检查失败样例对应的请求日志和容器日志')
    if warn_count > 0:
        risks.append('存在响应过短或耗时偏高的样例')
        recommendations.append('结合 smoke / benchmark 结果复核延迟与输出质量')
    if pass_count == len(cases) and cases:
        recommendations.append('可继续切换到 standard/deep 模式，或改用外部 Judge API 做更细致分析')
    if not cases:
        risks.append('未收集到有效质量样例')
        recommendations.append('检查 quality prompts 和服务接口响应')

    parsed = {
        'judge_mode': 'builtin',
        'overall_status': overall,
        'summary': summary,
        'cases': cases,
        'risks': risks,
        'recommendations': recommendations,
        'stats': {
            'pass_count': pass_count,
            'warn_count': warn_count,
            'fail_count': fail_count,
            'sample_count': len(cases),
            'service_base_url': base_url,
            'tested_model_id': model_id,
            'eval_mode': eval_mode,
        },
    }

    raw = {
        'timestamp': utc_timestamp(),
        'http_status': None,
        'latency_ms': None,
        'attempt': 1,
        'raw_response': {'mode': 'builtin'},
        'parsed_result': parsed,
    }
    write_json(Path(output_dir) / 'judge_eval_raw.json', raw)
    write_json(Path(output_dir) / 'judge_eval.json', parsed)
    write_final_brief(output_dir, parsed)
    return parsed


def run_judge_eval(api_base, api_key, judge_model, prompt_template_path, eval_mode, base_url, model_id, quality_prompts_path, sampled_outputs, output_dir, timeout_sec=180, judge_mode='builtin'):
    if judge_mode == 'builtin':
        return run_builtin_judge_eval(eval_mode, base_url, model_id, sampled_outputs, output_dir)

    prompt = build_judge_prompt(prompt_template_path, base_url, model_id, quality_prompts_path, sampled_outputs, eval_mode)
    result = call_judge_api(api_base, api_key, judge_model, prompt, timeout_sec=timeout_sec)
    write_json(Path(output_dir) / 'judge_eval_raw.json', result)
    parsed = result.get('parsed_result', {})
    write_json(Path(output_dir) / 'judge_eval.json', parsed)
    write_final_brief(output_dir, parsed)
    return parsed
