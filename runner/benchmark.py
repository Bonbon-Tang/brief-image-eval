import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from runner.utils import load_jsonl, utc_timestamp


def _extract_text(data):
    try:
        return data['choices'][0]['message']['content']
    except Exception:
        return str(data)[:2000]


def _chat_once(base_url, model, prompt, max_tokens=128):
    url = '{}/v1/chat/completions'.format(base_url)
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0,
        'max_tokens': max_tokens,
    }
    start = time.time()
    r = requests.post(url, json=payload, timeout=180)
    latency_ms = round((time.time() - start) * 1000, 2)
    data = r.json() if 'application/json' in r.headers.get('content-type', '') else {'raw': r.text}
    return {
        'status_code': r.status_code,
        'latency_ms': latency_ms,
        'response': data,
        'response_text': _extract_text(data),
    }


def run_smoke(base_url, model, prompts_path):
    prompts = load_jsonl(prompts_path)
    results = []
    passed = True
    for row in prompts:
        try:
            item = _chat_once(base_url, model, row['prompt'], max_tokens=64)
            item['id'] = row['id']
            item['category'] = row.get('category', 'smoke')
            results.append(item)
            if item['status_code'] != 200:
                passed = False
        except Exception as e:
            passed = False
            results.append({'id': row['id'], 'category': row.get('category', 'smoke'), 'error': str(e)})
    return {
        'stage': 'smoke',
        'timestamp': utc_timestamp(),
        'passed': passed,
        'results': results,
    }


def run_quality_samples(base_url, model, prompts_path):
    prompts = load_jsonl(prompts_path)
    results = []
    for row in prompts:
        try:
            item = _chat_once(base_url, model, row['prompt'], max_tokens=512)
            item['id'] = row['id']
            item['category'] = row.get('category', 'quality')
            item['prompt'] = row['prompt']
            results.append(item)
        except Exception as e:
            results.append({
                'id': row['id'],
                'category': row.get('category', 'quality'),
                'prompt': row['prompt'],
                'error': str(e),
            })
    return {
        'stage': 'quality_samples',
        'timestamp': utc_timestamp(),
        'results': results,
    }


def _run_concurrent_case(base_url, model, prompt, max_tokens, concurrency):
    latencies = []
    success = 0
    failures = []
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(_chat_once, base_url, model, prompt, max_tokens) for _ in range(concurrency)]
        for fut in as_completed(futures):
            try:
                res = fut.result()
                latencies.append(res['latency_ms'])
                if res['status_code'] == 200:
                    success += 1
                else:
                    failures.append(res)
            except Exception as e:
                failures.append({'error': str(e)})
    return {
        'concurrency': concurrency,
        'success_count': success,
        'failure_count': len(failures),
        'avg_latency_ms': round(sum(latencies) / len(latencies), 2) if latencies else None,
        'p95_latency_ms': round(statistics.quantiles(latencies, n=20)[18], 2) if len(latencies) >= 2 else (latencies[0] if latencies else None),
        'latencies_ms': latencies,
        'failures': failures[:3],
    }


def run_benchmark(base_url, model):
    cases = [
        {'name': 'short_c1', 'prompt': '请解释什么是 Transformer。', 'max_tokens': 128, 'concurrency': 1},
        {'name': 'short_c4', 'prompt': '请解释什么是 Transformer。', 'max_tokens': 128, 'concurrency': 4},
        {'name': 'long_c1', 'prompt': '请详细说明在真实 GPU 上验证大模型镜像时，为什么需要同时评估性能、稳定性和模型效果。', 'max_tokens': 512, 'concurrency': 1},
        {'name': 'long_c4', 'prompt': '请详细说明在真实 GPU 上验证大模型镜像时，为什么需要同时评估性能、稳定性和模型效果。', 'max_tokens': 512, 'concurrency': 4},
    ]
    results = []
    passed = True
    for case in cases:
        try:
            res = _run_concurrent_case(base_url, model, case['prompt'], case['max_tokens'], case['concurrency'])
            res['name'] = case['name']
            results.append(res)
            if res['failure_count'] > 0:
                passed = False
        except Exception as e:
            passed = False
            results.append({'name': case['name'], 'error': str(e)})
    return {
        'stage': 'benchmark',
        'timestamp': utc_timestamp(),
        'passed': passed,
        'results': results,
    }
