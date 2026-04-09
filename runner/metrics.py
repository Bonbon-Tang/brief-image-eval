import statistics
from typing import Any, Dict, List

from runner.utils import utc_timestamp


def _safe_mean(values: List[float]):
    return round(sum(values) / len(values), 2) if values else None


def _safe_p95(values: List[float]):
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return round(statistics.quantiles(values, n=20)[18], 2)


def _collect_success_latencies(smoke: Dict[str, Any], benchmark: Dict[str, Any], quality: Dict[str, Any]) -> List[float]:
    latencies = []
    for item in smoke.get('results', []):
        if item.get('status_code') == 200 and item.get('latency_ms') is not None:
            latencies.append(item['latency_ms'])
    for item in benchmark.get('results', []):
        for v in item.get('latencies_ms', []):
            if v is not None:
                latencies.append(v)
    for item in quality.get('results', []):
        if item.get('status_code') == 200 and item.get('latency_ms') is not None:
            latencies.append(item['latency_ms'])
    return latencies


def build_metrics(config: Dict[str, Any], smoke: Dict[str, Any], benchmark: Dict[str, Any], quality: Dict[str, Any], judge_eval: Dict[str, Any]) -> Dict[str, Any]:
    benchmark_results = benchmark.get('results', [])
    total_requests = 0
    total_success = 0
    total_failures = 0
    throughput_cases = []

    for item in benchmark_results:
        success = item.get('success_count', 0)
        failure = item.get('failure_count', 0)
        total = success + failure
        total_requests += total
        total_success += success
        total_failures += failure

        avg_latency_ms = item.get('avg_latency_ms')
        concurrency = item.get('concurrency', 0)
        throughput_rps = None
        if avg_latency_ms and avg_latency_ms > 0 and concurrency:
            throughput_rps = round(concurrency / (avg_latency_ms / 1000.0), 4)

        throughput_cases.append({
            'name': item.get('name'),
            'concurrency': concurrency,
            'avg_latency_ms': avg_latency_ms,
            'p95_latency_ms': item.get('p95_latency_ms'),
            'throughput_rps': throughput_rps,
            'success_count': success,
            'failure_count': failure,
        })

    all_latencies = _collect_success_latencies(smoke, benchmark, quality)
    avg_latency_ms = _safe_mean(all_latencies)
    p95_latency_ms = _safe_p95(all_latencies)
    success_rate = round(total_success / total_requests, 4) if total_requests else None

    judge_stats = judge_eval.get('stats', {}) if isinstance(judge_eval, dict) else {}
    accuracy_proxy = None
    if judge_stats.get('sample_count'):
        accuracy_proxy = round(judge_stats.get('pass_count', 0) / judge_stats.get('sample_count', 1), 4)

    smoke_total = len(smoke.get('results', []))
    smoke_success = sum(1 for item in smoke.get('results', []) if item.get('status_code') == 200)
    functionality_completeness = round(smoke_success / smoke_total, 4) if smoke_total else None

    return {
        'stage': 'metrics',
        'timestamp': utc_timestamp(),
        'service_base_url': config.get('base_url', ''),
        'tested_model_id': config.get('model_id', ''),
        'throughput': {
            'benchmark_cases': throughput_cases,
            'peak_rps': max((x['throughput_rps'] for x in throughput_cases if x['throughput_rps'] is not None), default=None),
        },
        'latency': {
            'avg_latency_ms': avg_latency_ms,
            'p95_latency_ms': p95_latency_ms,
        },
        'availability': {
            'total_requests': total_requests,
            'success_count': total_success,
            'failure_count': total_failures,
            'success_rate': success_rate,
        },
        'accuracy_proxy': {
            'judge_mode': judge_eval.get('judge_mode', 'builtin') if isinstance(judge_eval, dict) else 'builtin',
            'overall_status': judge_eval.get('overall_status', 'FAIL') if isinstance(judge_eval, dict) else 'FAIL',
            'pass_ratio': accuracy_proxy,
            'pass_count': judge_stats.get('pass_count'),
            'warn_count': judge_stats.get('warn_count'),
            'fail_count': judge_stats.get('fail_count'),
            'sample_count': judge_stats.get('sample_count'),
        },
        'functionality_completeness_proxy': {
            'smoke_passed': smoke.get('passed', False),
            'smoke_success_rate': functionality_completeness,
            'smoke_success_count': smoke_success,
            'smoke_total_count': smoke_total,
        },
        'energy_efficiency': {
            'status': 'NOT_COLLECTED',
            'notes': '当前版本未接入 GPU 功耗采集，需后续对接 nvidia-smi dmon / DCGM / 板卡遥测。',
        },
    }
