# brief-image-eval

一个面向真实 GPU 机器的镜像评测脚手架。

## 当前支持的五种运行方式

### 方式 A：官方镜像，项目自己起容器
- 使用 `vllm/vllm-openai:latest`
- 适合标准验证路径

### 方式 B：GPU 机器已有内网镜像，项目自己起容器
- 使用 `registry.h.pjlab.org.cn/ailab-sys/vllm:v0.17.1`
- 适合不再依赖 Docker Hub 的场景

### 方式 C：复用现有服务，项目不再新起容器
- 直接复用已经在跑的容器/服务
- 跳过镜像拉取、跳过 launch、跳过 cleanup
- 直接从 smoke / benchmark / quality / builtin judge 开始跑完整测试链路

### 方式 D：Linux + 4060 小模型联调
- 使用小模型先把项目链路跑通
- 适合 4060 这类消费级显卡
- 目标是验证项目流程，不是产出 H200 正式性能结论

### 方式 E：Windows + 4060 小模型联调（当前新加）
- 适合在 Windows + Docker Desktop + RTX4060 环境上先跑通流程
- 推荐直接使用 `python run_eval.py ...`
- 不依赖 bash 脚本

## Windows + 4060 推荐配置

新增配置文件：

```text
configs/images/windows_rtx4060_qwen25_0p5b_vllm.json
```

推荐文档：

```text
docs/WINDOWS_4060_QUICKSTART.md
```

核心思路：

- 镜像：`vllm/vllm-openai:latest`
- 模型：`Qwen/Qwen2.5-0.5B-Instruct`
- `max_model_len=4096`
- `gpu_memory_utilization=0.8`
- 用小模型先让整个项目跑通

> 这条路线的目标是验证流程，不是替代 H200 正式评测结果。

## 快速开始

### Windows + RTX4060

建议直接在项目目录执行：

```powershell
pip install -r requirements.txt
python run_eval.py --config configs/images/windows_rtx4060_qwen25_0p5b_vllm.json --judge-mode builtin --eval-mode quick
```

### Linux / 通用方式

如果你使用 Linux 或已有其它 GPU 配置，仍然可以使用原有方式：

```bash
python3 run_eval.py --config <your-config.json> --judge-mode builtin --eval-mode quick
```

## 常用配置文件

- `configs/images/h200_qwen25_3b_vllm.json` — H200 参考配置
- `configs/images/h200_existing_pjlab_vllm.json` — GPU 机已有内网镜像
- `configs/images/h200_reuse_existing_service.json` — 复用现有服务
- `configs/images/rtx4060_qwen25_0p5b_vllm.json` — Linux + 4060 小模型联调
- `configs/images/windows_rtx4060_qwen25_0p5b_vllm.json` — Windows + 4060 小模型联调

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

## 文档

- `docs/WINDOWS_4060_QUICKSTART.md`
- `docs/H200_RUN_GUIDE.md`
- `docs/PROJECT_START_GUIDE.md`
