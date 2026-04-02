
import subprocess
from typing import Any, Dict

from runner.utils import run_cmd, utc_timestamp


def _safe_run(cmd, timeout=60):
    try:
        cp = run_cmd(cmd, timeout=timeout, check=False)
        return {
            'returncode': cp.returncode,
            'stdout': cp.stdout.strip(),
            'stderr': cp.stderr.strip(),
        }
    except Exception as e:
        return {
            'returncode': -1,
            'stdout': '',
            'stderr': str(e),
        }


def run_preflight(config: Dict[str, Any]) -> Dict[str, Any]:
    image_uri = config['image_uri']

    docker_version = _safe_run(['docker', '--version'])
    nvidia_smi = _safe_run(['nvidia-smi'])
    gpu_query = _safe_run([
        'nvidia-smi',
        '--query-gpu=name,driver_version,memory.total',
        '--format=csv,noheader'
    ])
    docker_inspect = _safe_run(['docker', 'image', 'inspect', image_uri])

    passed = docker_version['returncode'] == 0 and nvidia_smi['returncode'] == 0

    return {
        'stage': 'preflight',
        'timestamp': utc_timestamp(),
        'passed': passed,
        'checks': {
            'docker_version': docker_version,
            'nvidia_smi': nvidia_smi,
            'gpu_query': gpu_query,
            'docker_image_inspect': docker_inspect,
        },
        'issues': [] if passed else ['docker 或 nvidia-smi 检查失败'],
    }
