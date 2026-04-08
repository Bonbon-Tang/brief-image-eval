# brief-image-eval

一个面向真实 H200 机器的镜像评测脚手架。

## 当前默认设计

这个项目现在默认按**内置评测流程**运行，不强依赖外部 Judge API：

- 默认 `JUDGE_MODE=builtin`
- 可以在开发机上先联网执行 `docker pull`
- 如果目标机器 pull 失败，但本地已经存在镜像缓存，可继续执行
- 仍然保留 `JUDGE_MODE=api` 能力，供后续接外部评测模型使用

也就是说，当前更适合的工程流程是：

1. 在可联网开发机上提前拉好镜像
2. 在目标 H200 机器上保留本地镜像
3. 项目默认走内置评测逻辑，先验证完整链路
4. 后续如果需要更细致的自动评价，再切到外部 Judge API

## 当前推荐镜像方案

### 方案 A：通用官方镜像

- 镜像：`vllm/vllm-openai:latest`
- 模型：`Qwen/Qwen2.5-3B-Instruct`
- 配置文件：`configs/images/h200_qwen25_3b_vllm.json`

### 方案 B：GPU 机器已有内网镜像（当前更适合你）

- 镜像：`registry.h.pjlab.org.cn/ailab-sys/vllm:v0.17.1`
- 模型：`Qwen/Qwen2.5-3B-Instruct`
- 配置文件：`configs/images/h200_existing_pjlab_vllm.json`

该方案适用于：

- 目标 H200 机器已经存在该镜像
- 不想再拉 Docker Hub
- 希望直接在 GPU 机上启动 `brief-image-eval` 项目本身，跑完整测试链路
- 不影响已有容器，使用单独端口和单独 GPU 做测试

## 完整流程

1. 读取镜像配置
2. 尝试 `docker pull` 验证镜像可拉取
3. 如 pull 失败但本地已有镜像缓存，可继续执行
4. 执行 preflight 检查（docker / nvidia-smi / 镜像信息）
5. 启动被测推理服务
6. 执行 smoke test
7. 执行 benchmark
8. 执行 quality samples
9. 使用内置评测逻辑（或可选外部 Judge API）生成分析结果
10. 生成 summary.json / report.md / final_brief.md
11. 清理容器
12. 在终端直接打印最终摘要

## 快速开始

### 1. 环境准备

建议在真实 H200 机器上准备：

- Linux
- Docker
- NVIDIA Driver
- NVIDIA Container Toolkit
- Python 3.8+
- 能访问 Hugging Face（匿名下载公开模型）

基础检查：

```bash
nvidia-smi
docker --version
python3 --version
```

安装 Python 依赖：

```bash
cd /root/.openclaw/workspace/brief-image-eval
pip3 install -r requirements.txt
```

### 2. 准备环境变量

```bash
cp .env.example .env
```

如果你要直接使用 GPU 机器上已有的内网镜像，推荐最小配置：

```bash
EVAL_MODE=quick
JUDGE_MODE=builtin
IMAGE_CONFIG=configs/images/h200_existing_pjlab_vllm.json
```

说明：

- 当前默认配置**不要求**填写 `HF_TOKEN`
- 当前默认配置**不要求**填写 Judge API
- 默认走公开模型匿名拉取 + 内置评测逻辑

如果你想启用外部 Judge API，再额外填写：

```bash
JUDGE_MODE=api
JUDGE_API_BASE=https://api.mooko.ai/v1
JUDGE_API_KEY=YOUR_API_KEY
JUDGE_MODEL=mooko/gpt-5.4
```

### 3. 使用 GPU 机已有镜像配置

当前已经提供可直接使用的配置文件：

```text
configs/images/h200_existing_pjlab_vllm.json
```

关键内容：

- `image_uri`: `registry.h.pjlab.org.cn/ailab-sys/vllm:v0.17.1`
- `launch_mode`: `vllm_serve_entrypoint`
- `model_id`: `Qwen/Qwen2.5-3B-Instruct`
- `host_port`: `18080`
- `container_port`: `8000`
- `healthcheck_path`: `/v1/models`
- `allow_cached_image_on_pull_failure`: `true`

额外参数：

- `--gpus device=7`，尽量避免影响现有容器
- 挂载 `/root/.cache/huggingface`
- `--ipc=host`

> 如果 GPU 7 已被占用，请把配置文件里的 `device=7` 改成别的空闲 GPU。

### 4. 直接启动项目本身

如果你沿用上面的 GPU 本地镜像配置，那么直接执行：

```bash
bash scripts/start_eval.sh
```

或者显式执行：

```bash
python3 run_eval.py \
  --config configs/images/h200_existing_pjlab_vllm.json \
  --judge-mode builtin \
  --eval-mode quick
```

这会直接启动 `brief-image-eval` 项目本身，而不是让你手动单独起服务。

## 如何交互

这个项目的交互分三层：

### 1. 你和项目交互

通过：

- `bash scripts/start_eval.sh`
- 或 `python3 run_eval.py ...`

### 2. 项目和被测镜像交互

项目会启动容器，并访问：

- `GET /v1/models` 做 readiness 检查
- `POST /v1/chat/completions` 做推理请求

因此被测镜像需要提供 OpenAI 兼容接口。

### 3. 项目和评测逻辑交互

默认是：

- **内置评测逻辑**：不依赖外部 API，直接根据样例结果生成 PASS/WARN/FAIL 与建议

可选是：

- **外部 Judge API**：调用外部模型做更细致的分析总结

## 评测模式

- `quick`：快速检查，适合先看镜像是否基本可用
- `standard`：标准评测，适合日常工程验证
- `deep`：深度评测，适合更完整地给出风险与建议

## 输出

所有结果写入：

```text
outputs/<run_id>/
```

包含：

- `meta.json`
- `preflight.json`
- `launch.json`
- `smoke.json`
- `benchmark.json`
- `quality_samples.json`
- `judge_eval_raw.json`
- `judge_eval.json`
- `summary.json`
- `report.md`
- `final_brief.md`

其中：

- `report.md`：完整报告
- `final_brief.md`：更适合快速阅读的摘要结论
- 终端执行完成后也会直接打印 `final_brief.md`

## 常见问题

### 1. `docker pull` 失败

说明目标机器无法直接访问镜像仓库。

处理建议：

- 如果本地镜像已存在，当前项目允许继续执行
- 或改用你们 GPU 机已经存在的内网镜像配置
- 不要在网络不通时反复硬拉 Docker Hub

### 2. 容器启动但 readiness 一直失败

通常是：

- 服务没在 8000 端口监听
- `/v1/models` 不存在
- 模型还没加载完
- 公开模型匿名下载失败
- 当前镜像入口方式与项目 launch 模式不匹配

### 3. 需要更强的自动质量分析

默认内置评测逻辑已经够做第一轮链路验证。

如果需要更细的自动评价，再开启：

```bash
JUDGE_MODE=api
```

并配置对应 Judge API 参数。

## 文档

- `configs/images/README.md`
- `docs/H200_RUN_GUIDE.md`
- `docs/PROJECT_START_GUIDE.md`
