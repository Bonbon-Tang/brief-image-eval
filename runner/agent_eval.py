
import json
from pathlib import Path
from typing import Any, Dict

from runner.utils import load_jsonl


def build_agent_task(base_url: str, model_id: str, quality_prompts_path: str, prompt_template_path: str, output_path: str) -> str:
    cases = load_jsonl(quality_prompts_path)
    template = Path(prompt_template_path).read_text(encoding='utf-8')
    payload = {
        'service_base_url': base_url,
        'model_id': model_id,
        'quality_cases': cases,
        'required_output_path': output_path,
    }
    task = template + '\n\n上下文(JSON):\n' + json.dumps(payload, ensure_ascii=False, indent=2) + '\n\n请直接完成评测，并将最终 JSON 结果写入 required_output_path 指定文件。'
    return task


def load_agent_result(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {
            'overall_status': 'FAIL',
            'summary': 'agent 未生成结果文件',
            'cases': [],
            'risks': ['agent 结果缺失'],
            'recommendations': ['检查 agent 会话日志'],
        }
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        return {
            'overall_status': 'FAIL',
            'summary': f'agent 结果文件解析失败: {e}',
            'cases': [],
            'risks': ['agent 输出非合法 JSON'],
            'recommendations': ['修复 agent 输出格式'],
        }
