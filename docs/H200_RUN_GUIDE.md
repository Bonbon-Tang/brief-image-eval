# H200 运行说明

这份文档的目标不是追求极限性能，而是先把 **GitHub → 联网开发机 → H200 → benchmark 结果** 这条链路稳定跑通。

## 推荐链路

1. **当前开发机**：改代码、提交 Git、推送 GitHub
2. **联网开发机**：拉代码、构建 runner 镜像，必要时把镜像或代码传到 H200
3. **H200**：直接执行 benchmark，产出结果目录

## H200 目标环境

建议在真实 H200 机器上准备：

- Linux
- Docker
- NVIDIA Driver
- NVIDIA Container Toolkit
- Python 3.10+

基础检查：

```bash
nvidia-smi
docker --version
python3 --version
```

---

## 方案 A：直接在 H200 上跑代码目录（最简单，推荐先打通）

### 1. 获取代码

可以在 H200 上直接 `git clone`，也可以从联网开发机 `scp` 代码目录过来。

### 2. 安装依赖

```bash
cd brief-image-eval
pip3 install -r requirements.txt
```

### 3. 选择配置

如果只是测通整个流程，优先用：

- `configs/images/h200_qwen25_3b_vllm.json`：项目自己起 vLLM 容器
- `configs/images/h200_reuse_existing_service.json`：复用 H200 上已经在跑的服务

### 4. 执行 benchmark

内置评测模式（不依赖外部 Judge API）：

```bash
bash scripts/run_h200_benchmark.sh
```

如果要复用已有服务：

```bash
IMAGE_CONFIG=configs/images/h200_reuse_existing_service.json \
JUDGE_MODE=builtin \
EVAL_MODE=quick \
bash scripts/run_h200_benchmark.sh
```

如果要用外部 Judge API：

```bash
IMAGE_CONFIG=configs/images/h200_qwen25_3b_vllm.json \
JUDGE_MODE=api \
JUDGE_API_BASE=https://api.mooko.ai/v1 \
JUDGE_API_KEY=YOUR_KEY \
JUDGE_MODEL=mooko/gpt-5.4 \
EVAL_MODE=quick \
bash scripts/run_h200_benchmark.sh
```

---

## 方案 B：在联网开发机构建 runner 镜像，再传到 H200

这个镜像是 **评测 runner 自身**，不是被测模型镜像。

### 1. 联网开发机构建

```bash
git clone <your-repo-url>
cd brief-image-eval
docker build -t brief-image-eval-runner:latest .
```

### 2. 导出并传到 H200

```bash
docker save brief-image-eval-runner:latest | gzip > brief-image-eval-runner.tar.gz
scp brief-image-eval-runner.tar.gz <user>@<h200-host>:/path/to/
```

### 3. H200 导入

```bash
gunzip -c brief-image-eval-runner.tar.gz | docker load
```

### 4. 以宿主机 Docker Socket 模式运行 runner

> 因为 runner 需要在 H200 上继续 `docker pull` / `docker run` 被测模型镜像，所以要挂 Docker Socket。

```bash
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/outputs:/app/outputs \
  -v /root/.cache/huggingface:/root/.cache/huggingface \
  brief-image-eval-runner:latest \
  python run_eval.py --config configs/images/h200_qwen25_3b_vllm.json --judge-mode builtin --eval-mode quick
```

如果 H200 上已经有现成服务可复用：

```bash
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/outputs:/app/outputs \
  brief-image-eval-runner:latest \
  python run_eval.py --config configs/images/h200_reuse_existing_service.json --judge-mode builtin --eval-mode quick
```

---

## 输出结果

所有结果默认写入：

```text
outputs/<run_id>/
```

重点关注这些文件：

- `preflight.json`
- `launch.json`
- `smoke.json`
- `benchmark.json`
- `quality_samples.json`
- `summary.json`
- `report.md`
- `final_brief.md`

---

## 当前推荐目标

这次建议先验收这 4 件事：

1. H200 上能成功通过 `preflight`
2. 被测模型容器能成功拉起，或成功复用现有服务
3. `smoke + benchmark + quality` 全部执行完成
4. `outputs/<run_id>/` 下成功生成结果文件

只要这四件事成立，就算 benchmark 流程已经打通。

---

## 常见问题

### 1. docker pull 失败但机器上已有镜像

当前 preflight 支持：

- 拉取失败
- 但本地 `docker image inspect` 成功
- 且 `allow_cached_image_on_pull_failure=true`

这种情况下允许继续执行。

### 2. H200 上已经有共享推理服务，不想新起容器

使用：

```text
configs/images/h200_reuse_existing_service.json
```

会跳过镜像拉取、launch、cleanup，直接对现有服务发请求。

### 3. 首次只是为了测链路，不想引入外部 Judge API

直接使用：

```bash
JUDGE_MODE=builtin
```

这样先把主流程跑通，后面再切到 `api` 模式。
