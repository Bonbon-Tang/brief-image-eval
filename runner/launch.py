import subprocess
import time
from typing import Any, Dict

import requests

from runner.utils import utc_timestamp


def build_docker_command(config: Dict[str, Any]) -> list[str]:
    image_uri = config['image_uri']
    host_port = int(config.get('host_port', 18000))
    container_port = int(config.get('container_port', 8000))
    model_id = config['model_id']
    dtype = config.get('dtype', 'bfloat16')
    tp = int(config.get('tensor_parallel_size', 1))
    max_model_len = int(config.get('max_model_len', 32768))
    gmu = float(config.get('gpu_memory_utilization', 0.9))
    extra = config.get('docker_extra_args', [])
    launch_mode = config.get('launch_mode', 'legacy_model_flag')

    cmd = [
        'docker', 'run', '--gpus', 'all', '--rm', '-d',
        '-p', f'{host_port}:{container_port}',
        '--name', f"eval_{str(host_port)}",
    ]
    cmd.extend(extra)
    cmd.append(image_uri)

    if launch_mode == 'vllm_serve_entrypoint':
        cmd.extend([
            'serve', model_id,
            '--host', '0.0.0.0',
            '--port', str(container_port),
            '--dtype', dtype,
            '--tensor-parallel-size', str(tp),
            '--max-model-len', str(max_model_len),
            '--gpu-memory-utilization', str(gmu),
        ])
    else:
        cmd.extend([
            '--model', model_id,
            '--dtype', dtype,
            '--tensor-parallel-size', str(tp),
            '--max-model-len', str(max_model_len),
            '--gpu-memory-utilization', str(gmu),
        ])
    return cmd


def wait_until_ready(config: Dict[str, Any]) -> Dict[str, Any]:
    host_port = int(config.get('host_port', 18000))
    timeout_sec = int(config.get('startup_timeout_sec', 900))
    path = config.get('healthcheck_path', '/v1/models')
    url = f'http://127.0.0.1:{host_port}{path}'
    start = time.time()
    last_error = None

    while time.time() - start < timeout_sec:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                return {
                    'ready': True,
                    'url': url,
                    'latency_sec': round(time.time() - start, 2),
                    'status_code': r.status_code,
                    'body': r.text[:1000],
                }
        except Exception as e:
            last_error = str(e)
        time.sleep(5)

    return {
        'ready': False,
        'url': url,
        'latency_sec': round(time.time() - start, 2),
        'error': last_error or 'timeout',
    }


def launch_service(config: Dict[str, Any]) -> Dict[str, Any]:
    cmd = build_docker_command(config)
    cp = subprocess.run(cmd, capture_output=True, text=True)
    container_id = cp.stdout.strip()
    ready = wait_until_ready(config) if cp.returncode == 0 else {'ready': False, 'error': cp.stderr.strip()}
    return {
        'stage': 'launch',
        'timestamp': utc_timestamp(),
        'passed': cp.returncode == 0 and ready.get('ready', False),
        'command': cmd,
        'container_id': container_id,
        'stdout': cp.stdout.strip(),
        'stderr': cp.stderr.strip(),
        'ready_check': ready,
    }


def cleanup_service(config: Dict[str, Any]) -> Dict[str, Any]:
    host_port = int(config.get('host_port', 18000))
    name = f'eval_{host_port}'
    cp = subprocess.run(['docker', 'rm', '-f', name], capture_output=True, text=True)
    return {
        'stage': 'cleanup',
        'timestamp': utc_timestamp(),
        'passed': cp.returncode == 0,
        'stdout': cp.stdout.strip(),
        'stderr': cp.stderr.strip(),
    }
