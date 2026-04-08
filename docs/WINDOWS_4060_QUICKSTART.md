# Windows + RTX4060 Quickstart

这份说明用于在 Windows + RTX4060 环境上先把 `brief-image-eval` 的流程跑通。

## 目标

这里的目标不是复现 H200 的正式性能，而是：

- 验证项目能否启动
- 验证容器能否起来
- 验证 smoke / benchmark / quality / report 能否完整输出

推荐先使用小模型：

- `Qwen/Qwen2.5-0.5B-Instruct`

对应配置文件：

```text
configs/images/windows_rtx4060_qwen25_0p5b_vllm.json
```

---

## 前提条件

建议你在 Windows 上满足这些条件：

1. 已安装 Docker Desktop
2. Docker Desktop 已启用 GPU 支持
3. `docker run --gpus all` 可正常工作
4. 本机可访问 Hugging Face（或已有缓存）
5. 已安装 Python 3.10+

先做基础检查：

```powershell
docker --version
python --version
nvidia-smi
```

如果 Docker GPU 是否可用不确定，可以先试：

```powershell
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

---

## 安装依赖

在项目目录下：

```powershell
pip install -r requirements.txt
```

---

## 配置方式一：直接命令行启动（推荐）

Windows 下建议优先直接运行 Python 命令，而不是依赖 bash 脚本。

```powershell
python run_eval.py --config configs/images/windows_rtx4060_qwen25_0p5b_vllm.json --judge-mode builtin --eval-mode quick
```

这会：

- 使用 `vllm/vllm-openai:latest`
- 加载 `Qwen/Qwen2.5-0.5B-Instruct`
- 在本机启动推理服务
- 跑 smoke / benchmark / quality
- 生成 `final_brief.md`

---

## 配置方式二：使用 `.env`

如果你仍想保留 `.env` 方式，可以在项目目录手动创建 `.env`：

```env
EVAL_MODE=quick
JUDGE_MODE=builtin
IMAGE_CONFIG=configs/images/windows_rtx4060_qwen25_0p5b_vllm.json
```

然后仍建议直接运行：

```powershell
python run_eval.py --config configs/images/windows_rtx4060_qwen25_0p5b_vllm.json --judge-mode builtin --eval-mode quick
```

> 当前仓库里的 `scripts/start_eval.sh` 是 bash 脚本，更适合 Linux/macOS。Windows 下优先直接用 `python run_eval.py ...`。

---

## 为什么这套参数适合 4060

当前配置里：

- 模型较小：`0.5B`
- `max_model_len=4096`
- `gpu_memory_utilization=0.8`
- `tensor_parallel_size=1`

这套更偏“先跑通”，不是追求极限性能。

---

## 输出结果

运行后结果会在：

```text
outputs/<run_id>/
```

重点看：

- `preflight.json`
- `launch.json`
- `smoke.json`
- `benchmark.json`
- `judge_eval.json`
- `final_brief.md`

---

## 常见问题

### 1. Docker GPU 不可用

如果 `docker run --gpus all ... nvidia-smi` 都失败，先不要跑项目，先修 Docker Desktop 的 GPU 支持。

### 2. 模型拉取慢/失败

说明本机访问 Hugging Face 有问题。可以：

- 先确认网络
- 先手工拉取镜像
- 或提前准备缓存

### 3. 4060 显存不够

先不要换大模型，优先保持：

- `Qwen/Qwen2.5-0.5B-Instruct`
- `max_model_len=4096`
- `quick` 模式

---

## 结论

Windows + 4060 方案的意义是：

- 验证 `brief-image-eval` 流程
- 验证脚本和配置
- 验证报告产出

不是用来替代 H200 的正式评测结果。
