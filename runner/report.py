def build_summary(config, run_id, preflight, launch, smoke, benchmark, judge_eval, metrics):
    overall = all([
        preflight.get('passed', False),
        launch.get('passed', False),
        smoke.get('passed', False),
        benchmark.get('passed', False),
        judge_eval.get('overall_status') in ('PASS', 'WARN'),
    ])
    return {
        'run_id': run_id,
        'image_uri': config['image_uri'],
        'model_id': config['model_id'],
        'gpu_type': config.get('gpu_type', 'unknown'),
        'preflight_passed': preflight.get('passed', False),
        'launch_passed': launch.get('passed', False),
        'smoke_passed': smoke.get('passed', False),
        'benchmark_passed': benchmark.get('passed', False),
        'judge_eval_status': judge_eval.get('overall_status', 'FAIL'),
        'overall_status': 'PASS' if overall else 'FAIL',
        'metrics': metrics,
    }


def build_markdown(summary, preflight, launch, smoke, benchmark, judge_eval, metrics):
    lines = []
    lines.append('# H200 镜像评测报告')
    lines.append('')
    lines.append('- Run ID: {}'.format(summary['run_id']))
    lines.append('- 镜像: {}'.format(summary['image_uri']))
    lines.append('- 模型: {}'.format(summary['model_id']))
    lines.append('- GPU: {}'.format(summary['gpu_type']))
    lines.append('- 总体结论: {}'.format(summary['overall_status']))
    lines.append('')
    lines.append('## 预检查')
    lines.append('- 结果: {}'.format('PASS' if preflight.get('passed') else 'FAIL'))
    lines.append('')
    lines.append('## 启动检查')
    lines.append('- 结果: {}'.format('PASS' if launch.get('passed') else 'FAIL'))
    lines.append('')
    lines.append('## Smoke Test')
    lines.append('- 结果: {}'.format('PASS' if smoke.get('passed') else 'FAIL'))
    lines.append('')
    lines.append('## Benchmark')
    for item in benchmark.get('results', []):
        total = item.get('success_count', 0) + item.get('failure_count', 0)
        lines.append('- {}: avg={}ms p95={}ms success={}/{}'.format(
            item.get('name'), item.get('avg_latency_ms'), item.get('p95_latency_ms'), item.get('success_count'), total
        ))
    lines.append('')
    lines.append('## 指标采集汇总')
    lines.append('- 吞吐峰值 (RPS): {}'.format(metrics.get('throughput', {}).get('peak_rps')))
    lines.append('- 平均延迟 (ms): {}'.format(metrics.get('latency', {}).get('avg_latency_ms')))
    lines.append('- P95 延迟 (ms): {}'.format(metrics.get('latency', {}).get('p95_latency_ms')))
    lines.append('- 请求成功率: {}'.format(metrics.get('availability', {}).get('success_rate')))
    lines.append('- 准确率代理 (PASS ratio): {}'.format(metrics.get('accuracy_proxy', {}).get('pass_ratio')))
    lines.append('- 功能完备性代理 (smoke 成功率): {}'.format(metrics.get('functionality_completeness_proxy', {}).get('smoke_success_rate')))
    lines.append('- 能效比采集状态: {}'.format(metrics.get('energy_efficiency', {}).get('status')))
    lines.append('')
    lines.append('## API 评测结果')
    lines.append('- 结果: {}'.format(judge_eval.get('overall_status', 'FAIL')))
    if judge_eval.get('summary'):
        lines.append('- 总结: {}'.format(judge_eval['summary']))
    for case in judge_eval.get('cases', []):
        lines.append('- {}: {} - {}'.format(case.get('id'), case.get('verdict'), case.get('notes')))
    if judge_eval.get('risks'):
        lines.append('')
        lines.append('## 风险')
        for risk in judge_eval['risks']:
            lines.append('- {}'.format(risk))
    if judge_eval.get('recommendations'):
        lines.append('')
        lines.append('## 建议')
        for r in judge_eval['recommendations']:
            lines.append('- {}'.format(r))
    lines.append('')
    return '\n'.join(lines)
