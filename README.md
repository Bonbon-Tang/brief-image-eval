# brief-image-eval

一个面向真实 GPU 机器的镜像评测脚手架。

当前仓库已经按 **H200 复用已有服务** 的真实可执行链路固化。

当前验证通过的服务形态是：

- 容器：`caikun-dlrouter`
- 网络：`host`
- 镜像：`registry.h.pjlab.org.cn/ailab-sys/vllm:v0.17.1`
- 本地模型目录：`/mnt/nvme1n1/ml_research/models_4/qwen3-0.6b-local`
- 服务地址：`http://127.0.0.1:18080`

> 重要：`run_eval.py` 必须在 **H200 宿主机** 执行，不要在被测 vLLM 容器里执行。

---

## 一、在 caikun-dlrouter 容器内启动服务

先进入容器：

```bash
docker exec -it caikun-dlrouter /bin/bash
```

在容器内执行：

```bash
vllm serve /mnt/nvme1n1/ml_research/models_4/qwen3-0.6b-local \
  --host 0.0.0.0 \
  --port 18080 \
  --dtype bfloat16 \
  --tensor-parallel-size 1 \
  --max-model-len 2048 \
  --gpu-memory-utilization 0.6
```

---

## 二、在 H200 宿主机确认服务可访问

```bash
curl http://127.0.0.1:18080/v1/models
```

当前预期返回模型 ID：

```text
/mnt/nvme1n1/ml_research/models_4/qwen3-0.6b-local
```

---

## 三、在 H200 宿主机执行 benchmark

进入项目目录：

```bash
cd /mnt/nvme1n1/tangyufeng/brief-image-eval
```

安装依赖：

```bash
pip3 install -r requirements.txt
```

执行 benchmark：

```bash
python3 run_eval.py \
  --config configs/images/h200_reuse_existing_service.json \
  --judge-mode builtin \
  --eval-mode quick
```

或者：

```bash
IMAGE_CONFIG=configs/images/h200_reuse_existing_service.json \
JUDGE_MODE=builtin \
EVAL_MODE=quick \
bash scripts/run_h200_benchmark.sh
```

---

## 四、结果目录

结果会写到：

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

查看最近一次输出：

```bash
ls -td outputs/* | head
```

查看最终摘要：

```bash
cat outputs/<run_id>/final_brief.md
```

---

## 五、当前阶段目标

当前目标是 **方向 A：先确认链路可复现**。

所以当前成功标准是：

1. `curl /v1/models` 可通
2. `run_eval.py` 能完整跑完
3. `outputs/<run_id>/` 能稳定生成

如果最终结论是 `FAIL`，但流程完整走通，也说明工程链已经打通；后续再分析失败样例、服务稳定性和模型效果。
