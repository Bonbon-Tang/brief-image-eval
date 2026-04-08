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


def run_preflight(config):
    image_uri = config['image_uri']
    allow_cached_image = bool(config.get('allow_cached_image_on_pull_failure', True))

    docker_version = _safe_run(['docker', '--version'])
    nvidia_smi = _safe_run(['nvidia-smi'])
    gpu_query = _safe_run([
        'nvidia-smi',
        '--query-gpu=name,driver_version,memory.total',
        '--format=csv,noheader'
    ])
    docker_pull = _safe_run(['docker', 'pull', image_uri], timeout=1800)
    docker_inspect = _safe_run(['docker', 'image', 'inspect', image_uri])

    pull_ok = docker_pull['returncode'] == 0
    inspect_ok = docker_inspect['returncode'] == 0
    image_ready = pull_ok or (allow_cached_image and inspect_ok)

    passed = (
        docker_version['returncode'] == 0 and
        nvidia_smi['returncode'] == 0 and
        image_ready
    )

    issues = []
    warnings = []
    if docker_version['returncode'] != 0:
        issues.append('docker 检查失败')
    if nvidia_smi['returncode'] != 0:
        issues.append('nvidia-smi 检查失败')
    if docker_pull['returncode'] != 0:
        if inspect_ok and allow_cached_image:
            warnings.append('镜像拉取失败，但检测到本地已有缓存镜像，允许继续执行')
        else:
            issues.append('镜像拉取失败，请确认 image_uri 真实存在且可直接拉取，或先在开发机拉取后导入本机')
    if docker_inspect['returncode'] != 0 and not pull_ok:
        issues.append('镜像 inspect 失败，本地不存在可用镜像')

    return {
        'stage': 'preflight',
        'timestamp': utc_timestamp(),
        'passed': passed,
        'checks': {
            'docker_version': docker_version,
            'nvidia_smi': nvidia_smi,
            'gpu_query': gpu_query,
            'docker_pull': docker_pull,
            'docker_image_inspect': docker_inspect,
        },
        'policy': {
            'allow_cached_image_on_pull_failure': allow_cached_image,
            'image_ready': image_ready,
        },
        'issues': issues,
        'warnings': warnings,
    }
