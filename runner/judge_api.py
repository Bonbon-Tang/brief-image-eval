import json
import time
from pathlib import Path

import requests

from runner.utils import load_jsonl, utc_timestamp, write_json


def call_judge_api(api_base, api_key, model, prompt_text, timeout_sec=180):
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
    start = time.time()
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout_sec)
    latency_ms = round((time.time() - start) * 1000, 2)
    text = resp.text
    data = None
    try:
        raw = resp.json()
        text = raw['choices'][0]['message']['content']
    except Exception:
        raw = {'raw_text': resp.text}
    try:
        data = json.loads(text)
    except Exception:
        data = {
            'overall_status': 'FAIL',
            'summary': 'judge API 返回内容不是合法 JSON',
            'cases': [],
            'risks': ['judge API 输出格式异常'],
            'recommendations': ['检查 judge model 提示词或返回格式'],
            'raw_output': text,
        }
    return {
        'timestamp': utc_timestamp(),
        'http_status': resp.status_code,
        'latency_ms': latency_ms,
        'raw_response': raw,
        'parsed_result': data,
    }


def build_judge_prompt(base_url, model_id, quality_prompts_path, sampled_outputs):
    cases = load_jsonl(quality_prompts_path)
    payload = {
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
    return (
        '请基于以下被测模型输出，完成质量评测。\n'
        '要求：\n'
        '1. 输出必须是严格 JSON；\n'
        '2. 不要输出 Markdown；\n'
        '3. 不要省略任何 case；\n'
        '4. 对每个 case 判断是否完整、是否明显幻觉、是否符合问题要求；\n'
        '5. 最后给总体状态和建议。\n\n'
        '评测上下文：\n' + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def run_judge_eval(api_base, api_key, judge_model, base_url, model_id, quality_prompts_path, sampled_outputs, output_dir, timeout_sec=180):
    prompt = build_judge_prompt(base_url, model_id, quality_prompts_path, sampled_outputs)
    result = call_judge_api(api_base, api_key, judge_model, prompt, timeout_sec=timeout_sec)
    write_json(Path(output_dir) / 'judge_eval_raw.json', result)
    parsed = result.get('parsed_result', {})
    write_json(Path(output_dir) / 'judge_eval.json', parsed)
    return parsed
