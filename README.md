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
5. 默认使用内置评测逻辑，不强依赖外部 API

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

编辑 `.env`，最小可用配置：

```bash
EVAL_MODE=quick
JUDGE_MODE=builtin
IMAGE_CONFIG=configs/images/h200_qwen25_3b_vllm.json
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
- `allow_cached_image_on_pull_failure`: `true`

这里特别说明一下：

- **默认配置下，你不需要再手动填写真实镜像地址**
- 因为 `configs/images/h200_qwen25_3b_vllm.json` 里已经写好了：

```json
"image_uri": "vllm/vllm-openai:latest"
```

只有下面这种情况，才需要你自己改：

- 你想换成你们自己的部署镜像
- 你想换成别的官方镜像/tag
- 你要测试另一个模型对应的镜像方案

额外参数：

- 挂载 `/root/.cache/huggingface`
- `--ipc=host`

### 4. 推荐镜像准备方式

如果目标 H200 机器直接访问 Docker Hub 不稳定，**不要继续在目标机上硬拉 Docker Hub**，推荐改用下面的离线/中转方式。

#### 方式 A：开发机 pull → save tar → H200 load（推荐）

在可联网开发机上：

```bash
docker pull vllm/vllm-openai:latest
docker save -o vllm-vllm-openai-latest.tar vllm/vllm-openai:latest
```

把 tar 包传到目标 H200 机器后：

```bash
docker load -i vllm-vllm-openai-latest.tar
```

然后可以先确认本地镜像已存在：

```bash
docker image inspect vllm/vllm-openai:latest
```

或：

```bash
docker images | grep vllm
```

这样即使目标机 `docker pull` 失败，只要本地镜像已存在，preflight 也允许继续执行。

#### 方式 B：推到你们内网镜像仓库（更适合长期）

如果你们有内网 registry，推荐在开发机上：

```bash
docker pull vllm/vllm-openai:latest
docker tag vllm/vllm-openai:latest your-registry/brief-image-eval/vllm-openai:latest
docker push your-registry/brief-image-eval/vllm-openai:latest
```

然后把配置文件里的：

```json
"image_uri": "vllm/vllm-openai:latest"
```

改成：

```json
"image_uri": "your-registry/brief-image-eval/vllm-openai:latest"
```

这样目标 H200 机器就不需要直连 Docker Hub，而是从你们自己的镜像仓库拉取。

### 5. 一键启动

如果你沿用默认配置，那么做完 `.env` 后就可以直接启动：

```bash
bash scripts/start_eval.sh
```

如果你想显式指定内置评测模式，也可以这样：

```bash
python3 run_eval.py \
  --config configs/images/h200_qwen25_3b_vllm.json \
  --judge-mode builtin \
  --eval-mode quick
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

说明目标机器无法直接访问 Docker Hub。

处理建议：

- 不要继续在目标机上反复直接拉 Docker Hub
- 在开发机先 `docker pull`
- 再 `docker save` / `docker load` 导入到目标机
- 或改成你们内网 registry
- 当前项目允许 pull 失败但本地已有镜像时继续执行

### 2. 容器启动但 readiness 一直失败

通常是：

- 服务没在 8000 端口监听
- `/v1/models` 不存在
- 模型还没加载完
- 公开模型匿名下载失败

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
