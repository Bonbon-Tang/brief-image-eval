# Project Start Guide

这是一份面向当前项目的最小启动说明，目标是先在 H200 上跑通一个真实镜像的完整评测链路。

## 当前推荐首发组合

- 镜像：`vllm/vllm-openai:latest`
- 模型：`Qwen/Qwen2.5-3B-Instruct`
- 配置文件：`configs/images/h200_qwen25_3b_vllm.json`

选择这套组合的原因：

1. 镜像为 vLLM 官方镜像，真实可拉取
2. 当前项目启动参数与 vLLM OpenAI 兼容服务天然匹配
3. Qwen2.5-3B-Instruct 体量适中，适合先验证完整链路
4. 中文效果较稳，适合快速做 smoke / quality 验证

---

## 一、环境要求

建议在真实 H200 机器上准备：

- Linux
- Docker
- NVIDIA Driver
- NVIDIA Container Toolkit
- Python 3.8+
- 可访问 Hugging Face（或已准备好缓存）

先做基础检查：

```bash
nvidia-smi
docker --version
python3 --version
```

---

## 二、安装依赖

```bash
cd brief-image-eval
pip3 install -r requirements.txt
```

---

## 三、准备环境变量

复制模板：

```bash
cp .env.example .env
```

然后编辑 `.env`，至少填写：

```bash
JUDGE_API_BASE=https://api.mooko.ai/v1
JUDGE_API_KEY=YOUR_API_KEY
JUDGE_MODEL=mooko/gpt-5.4
EVAL_MODE=quick
IMAGE_CONFIG=configs/images/h200_qwen25_3b_vllm.json
```

### 字段说明

- `JUDGE_API_BASE`：Judge API 地址
- `JUDGE_API_KEY`：Judge API Key
- `JUDGE_MODEL`：Judge 模型名
- `EVAL_MODE`：评测模式，建议先用 `quick`
- `IMAGE_CONFIG`：被测镜像配置文件
- 当前默认配置不要求填写 `HF_TOKEN`，按公开模型匿名拉取方式启动

> 注意：当前 `scripts/start_eval.sh` 会自动加载 `.env`。

---

## 四、当前推荐配置文件

项目已提供：

```text
configs/images/h200_qwen25_3b_vllm.json
```

关键内容如下：

- `image_uri`: `vllm/vllm-openai:latest`
- `model_id`: `Qwen/Qwen2.5-3B-Instruct`
- `host_port`: `18000`
- `container_port`: `8000`
- `healthcheck_path`: `/v1/models`

并额外加入了：

- Hugging Face 缓存目录挂载
- `--ipc=host`

---

## 五、如何启动

### 方式 A：一键脚本（推荐）

```bash
bash scripts/start_eval.sh
```

这个脚本会：

1. 自动读取 `.env`
2. 校验 Judge API 配置
3. 调用 `run_eval.py`
4. 跑完整评测流程

### 方式 B：手动执行主入口

```bash
python3 run_eval.py \
  --config configs/images/h200_qwen25_3b_vllm.json \
  --judge-api-base https://api.mooko.ai/v1 \
  --judge-api-key YOUR_KEY \
  --judge-model mooko/gpt-5.4 \
  --eval-mode quick
```

适合调试或在 CI 环境中使用。

---

## 六、完整流程会发生什么

执行后，项目会按以下顺序运行：

1. 读取镜像配置
2. `docker pull vllm/vllm-openai:latest`
3. 检查 `docker` / `nvidia-smi`
4. 启动容器服务
5. 轮询 `http://127.0.0.1:18000/v1/models`
6. 执行 smoke test
7. 执行 benchmark
8. 执行 quality samples
9. 调用 Judge API 做质量分析
10. 生成报告并输出最终摘要
11. 默认清理容器

---

## 七、结果怎么看

每次运行会在下面生成结果目录：

```text
outputs/<run_id>/
```

重点文件：

- `preflight.json`：环境与镜像拉取检查
- `launch.json`：容器启动与 ready 检查
- `smoke.json`：冒烟测试结果
- `benchmark.json`：性能测试结果
- `quality_samples.json`：质量样例输出
- `judge_eval.json`：Judge 分析结果
- `summary.json`：汇总结果
- `report.md`：完整报告
- `final_brief.md`：简版结论

命令结束后，终端也会打印 `final_brief.md`。

---

## 八、如何交互

这个项目的“交互”分三层：

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

---

## 九、最常见问题

### 1. `docker pull` 失败

说明镜像地址不可拉取，或当前机器没有访问权限。

### 2. 容器启动但 readiness 一直失败

通常是：

- 服务没在 8000 端口监听
- `/v1/models` 不存在
- 模型还没加载完
- 匿名模型下载失败

### 3. 启动时报模型下载问题

优先检查：

- 当前机器是否能访问 Hugging Face
- `/root/.cache/huggingface` 是否可用
- 公开模型是否可匿名拉取

如果匿名拉取失败，再考虑补充 `HF_TOKEN` 方案

### 4. Judge API 缺失

如果没填 `JUDGE_API_BASE` 或 `JUDGE_API_KEY`，启动脚本会直接失败。

---

## 十、推荐操作顺序

第一轮建议只做：

1. 配置 `.env`
2. 使用 `configs/images/h200_qwen25_3b_vllm.json`
3. 运行 `quick` 模式
4. 确认完整链路已跑通
5. 再考虑切换到 7B 或你们后续正式模型

如果第一轮要更稳，先手动验证镜像：

```bash
docker pull vllm/vllm-openai:latest
```

如需进一步验证模型拉取，可在 H200 机器上单独手工跑一次 vLLM 容器，再回到本项目中走自动评测。
