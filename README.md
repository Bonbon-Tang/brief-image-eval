# brief-image-eval

一个面向真实 H200 机器的镜像评测脚手架。

## 你的两个核心要求

1. **镜像必须真实存在且可以直接拉取**
2. **本地只启动一个脚本，就能执行完整流程**

这个项目已经按这两个要求设计：

- `image_uri` 必须由你明确填写为真实可拉取镜像
- preflight 阶段会强制执行 `docker pull`
- 提供统一启动脚本：`scripts/start_eval.sh`
- 评测支持三种模式：`quick / standard / deep`
- 流程结束后终端会直接打印 `final_brief.md` 的核心结论

## 当前推荐首发组合

为了先把 H200 上的完整链路跑通，当前默认推荐：

- 镜像：`vllm/vllm-openai:latest`
- 模型：`Qwen/Qwen2.5-3B-Instruct`
- 配置文件：`configs/images/h200_qwen25_3b_vllm.json`

选择这套组合的原因：

1. vLLM 官方镜像真实可拉取
2. 当前项目启动参数与 vLLM OpenAI 兼容服务天然匹配
3. Qwen2.5-3B-Instruct 体量适中，适合先验证完整链路
4. 默认按公开模型匿名拉取，不强制要求 `HF_TOKEN`

## 完整流程

1. 读取镜像配置
2. 显式 `docker pull` 验证镜像真实可拉取
3. 执行 preflight 检查（docker / nvidia-smi / 镜像信息）
4. 启动被测推理服务
5. 执行 smoke test
6. 执行 benchmark
7. 按评测模式执行 quality samples
8. 调用外部 Judge API，对质量样例进行分析与总结
9. 生成 summary.json / report.md / final_brief.md
10. 清理容器
11. 在终端直接打印最终摘要

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

编辑 `.env`，至少填写：

```bash
JUDGE_API_BASE=https://api.mooko.ai/v1
JUDGE_API_KEY=YOUR_API_KEY
JUDGE_MODEL=mooko/gpt-5.4
EVAL_MODE=quick
IMAGE_CONFIG=configs/images/h200_qwen25_3b_vllm.json
```

说明：

- 当前默认配置**不要求**填写 `HF_TOKEN`
- 默认走公开模型匿名拉取
- 如果后续匿名拉取失败，再补充 `HF_TOKEN` 方案

### 3. 使用默认推荐配置

当前已经提供可直接使用的配置文件：

```text
configs/images/h200_qwen25_3b_vllm.json
```

关键内容：

- `image_uri`: `vllm/vllm-openai:latest`
- `model_id`: `Qwen/Qwen2.5-3B-Instruct`
- `host_port`: `18000`
- `container_port`: `8000`
- `healthcheck_path`: `/v1/models`

额外参数：

- 挂载 `/root/.cache/huggingface`
- `--ipc=host`

如果想先手动验证镜像：

```bash
docker pull vllm/vllm-openai:latest
```

### 4. 一键启动

```bash
bash scripts/start_eval.sh
```

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

### 3. 项目和 Judge API 交互

项目会把质量样例输出发给 Judge API，做自动分析总结。

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

说明镜像地址不可拉取，或当前机器没有访问权限。

### 2. 容器启动但 readiness 一直失败

通常是：

- 服务没在 8000 端口监听
- `/v1/models` 不存在
- 模型还没加载完
- 公开模型匿名下载失败

### 3. 启动时报模型下载问题

优先检查：

- 当前机器是否能访问 Hugging Face
- `/root/.cache/huggingface` 是否可用
- 当前模型是否允许匿名拉取

如果匿名拉取失败，再考虑补充 `HF_TOKEN`。

### 4. Judge API 缺失

如果没填 `JUDGE_API_BASE` 或 `JUDGE_API_KEY`，启动脚本会直接失败。

## 文档

- `configs/images/README.md`
- `docs/H200_RUN_GUIDE.md`
- `docs/PROJECT_START_GUIDE.md`
