# brief-image-eval

一个面向真实 GPU 机器的镜像评测脚手架。

当前目标不是追求极限性能，而是先把 **开发机 → H200 → benchmark 结果** 这条链路稳定跑通。

---

## 开发机需要做什么

开发机职责：

1. 拉取/更新代码
2. 构建评测 runner 镜像
3. 把代码或 runner 镜像传到 H200

### 1. 拉取代码

```bash
git clone <your-repo-url>
cd brief-image-eval
```

或者已有仓库时：

```bash
git pull
```

### 2. 构建 runner 镜像

```bash
docker build -t brief-image-eval-runner:latest .
```

> 这个镜像是 **评测 runner 本身**，不是被测模型镜像。
> 它的作用是在 H200 上统一执行 `run_eval.py`，并调用宿主机 Docker 去拉起被测模型镜像。

### 3. 导出 runner 镜像

```bash
docker save brief-image-eval-runner:latest | gzip > brief-image-eval-runner.tar.gz
```

### 4. 传到 H200

传镜像：

```bash
scp brief-image-eval-runner.tar.gz <user>@<h200-host>:/path/to/
```

如果也要传代码目录：

```bash
scp -r brief-image-eval <user>@<h200-host>:/path/to/
```

---

## H200 需要做什么

H200 职责：

1. 准备 Docker / NVIDIA 环境
2. 导入 runner 镜像，或直接使用代码目录
3. 执行 benchmark
4. 查看结果目录

### 1. 基础检查

```bash
nvidia-smi
docker --version
python3 --version
```

### 2. 两种执行方式

#### 方式 A：直接跑代码目录（最简单，推荐先打通）

进入项目目录并安装依赖：

```bash
cd brief-image-eval
pip3 install -r requirements.txt
```

直接执行：

```bash
bash scripts/run_h200_benchmark.sh
```

如果复用 H200 上已经存在的推理服务：

```bash
IMAGE_CONFIG=configs/images/h200_reuse_existing_service.json bash scripts/run_h200_benchmark.sh
```

#### 方式 B：使用开发机构建好的 runner 镜像

导入镜像：

```bash
gunzip -c brief-image-eval-runner.tar.gz | docker load
```

运行 runner：

```bash
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/outputs:/app/outputs \
  -v /root/.cache/huggingface:/root/.cache/huggingface \
  brief-image-eval-runner:latest \
  python run_eval.py --config configs/images/h200_qwen25_3b_vllm.json --judge-mode builtin --eval-mode quick
```

如果复用已有服务：

```bash
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/outputs:/app/outputs \
  brief-image-eval-runner:latest \
  python run_eval.py --config configs/images/h200_reuse_existing_service.json --judge-mode builtin --eval-mode quick
```

### 3. 输出结果

结果默认写入：

```text
outputs/<run_id>/
```

重点关注：

- `preflight.json`
- `launch.json`
- `smoke.json`
- `benchmark.json`
- `quality_samples.json`
- `summary.json`
- `report.md`
- `final_brief.md`

---

## 推荐配置

- `configs/images/h200_qwen25_3b_vllm.json`：H200 自己拉起 vLLM 容器
- `configs/images/h200_reuse_existing_service.json`：复用 H200 上已有服务

---

## 当前建议

第一次先用：

- `JUDGE_MODE=builtin`
- `EVAL_MODE=quick`

先把主链路跑通，再决定要不要切到外部 Judge API。
