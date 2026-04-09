# brief-image-eval

一个面向真实 GPU 机器的镜像评测脚手架。

当前这版仓库已经按 **H200 直接执行** 的方式固化，目标是先稳定完成：

1. 用 H200 上已有镜像启动服务
2. 在宿主机运行 benchmark runner
3. 输出完整评测结果

> 重要：`run_eval.py` 要在 **H200 宿主机** 执行，不要在被测 vLLM 容器里执行。

---

## 一、当前默认测试组合

- 被测镜像：`registry.h.pjlab.org.cn/ailab-sys/vllm:v0.17.1`
- 宿主机挂载目录：`/mnt/nvme1n1/tangyufeng`
- 模型目录：`/mnt/nvme1n1/tangyufeng/models/Qwen2.5-0.5B-Instruct`
- 服务端口：`18080`
- runner 配置：`configs/images/h200_reuse_existing_service.json`
- 评测模式：`builtin + quick`

---

## 二、H200 直接执行命令

### 1. 启动被测服务

```bash
docker rm -f brief-image-eval-vllm 2>/dev/null || true

docker run --rm -d \
  --name brief-image-eval-vllm \
  --gpus all \
  --ipc=host \
  --mount type=bind,source=/mnt/nvme1n1/tangyufeng,target=/mnt/nvme1n1/tangyufeng \
  -p 18080:8000 \
  registry.h.pjlab.org.cn/ailab-sys/vllm:v0.17.1 \
  serve /mnt/nvme1n1/tangyufeng/models/Qwen2.5-0.5B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype bfloat16 \
  --tensor-parallel-size 1 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.8
```

如果你们要固定单卡，比如 GPU 7，把 `--gpus all` 改成：

```bash
--gpus '"device=7"'
```

### 2. 检查服务是否就绪

```bash
curl http://127.0.0.1:18080/v1/models
```

只要这条返回 JSON，就说明服务已经起来了。

### 3. 进入项目目录

```bash
cd /mnt/nvme1n1/tangyufeng/brief-image-eval
```

### 4. 安装 Python 依赖

```bash
pip3 install -r requirements.txt
```

### 5. 执行 benchmark

```bash
python3 run_eval.py \
  --config configs/images/h200_reuse_existing_service.json \
  --judge-mode builtin \
  --eval-mode quick
```

或者用脚本：

```bash
IMAGE_CONFIG=configs/images/h200_reuse_existing_service.json \
JUDGE_MODE=builtin \
EVAL_MODE=quick \
bash scripts/run_h200_benchmark.sh
```

---

## 三、查看结果

结果目录默认在：

```text
outputs/<run_id>/
```

重点文件：

```text
outputs/<run_id>/preflight.json
outputs/<run_id>/launch.json
outputs/<run_id>/smoke.json
outputs/<run_id>/benchmark.json
outputs/<run_id>/quality_samples.json
outputs/<run_id>/summary.json
outputs/<run_id>/report.md
outputs/<run_id>/final_brief.md
```

查看最近一次结果：

```bash
ls -td outputs/* | head
```

查看摘要：

```bash
cat outputs/<run_id>/final_brief.md
```

---

## 四、当前定位

当前目标是 **方向 A：先确认链路稳定可复现**，不是先追求高分。

也就是说，只要你能稳定完成：

1. 服务启动
2. runner 跑完
3. `outputs/<run_id>/` 生成结果

就说明 H200 的执行链已经打通。

后面再根据结果决定是否换更大的模型、调 prompt、调 benchmark 配置。
