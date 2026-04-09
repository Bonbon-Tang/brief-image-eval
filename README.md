# brief-image-eval

一个面向真实 GPU 机器的镜像评测脚手架。

当前仓库默认采用 **H200 复用已有服务** 模式，并维护两个默认镜像选项：

- `image0`：上一台已验证通过的镜像
- `image1`：当前新的默认镜像

> 重要：`run_eval.py` 必须在 **H200 宿主机** 执行，不要在被测 vLLM 容器里执行。

---

## 默认镜像选项

### image0

- 配置文件：`configs/images/image0_h200_reuse_existing_service.json`
- 容器：`caikun-dlrouter`
- 镜像：`registry.h.pjlab.org.cn/ailab-sys/vllm:v0.17.1`
- 模型：`/mnt/nvme1n1/ml_research/models_4/qwen3-0.6b-local`
- 状态：已实测 PASS

### image1（当前默认）

- 配置文件：`configs/images/image1_h200_reuse_existing_service.json`
- 默认评测配置：`configs/images/h200_reuse_existing_service.json`
- 容器：`yuansheng`
- 镜像：`registry.h.pjlab.org.cn/ailab-pj/vllm:0.16.2rc2.g21dfb842d.cu128`
- 模型：`/mnt/nvme1n1/ml_research/models_4/qwen3-0.6b-local`
- 说明：启动服务前需设置 `FLASHINFER_DISABLE_VERSION_CHECK=1`

---

## image1 启动服务方式

先进入容器：

```bash
docker exec -it yuansheng /bin/bash
```

在容器内执行：

```bash
export FLASHINFER_DISABLE_VERSION_CHECK=1
export CUDA_VISIBLE_DEVICES=<空闲GPU编号>

vllm serve /mnt/nvme1n1/ml_research/models_4/qwen3-0.6b-local \
  --host 0.0.0.0 \
  --port 18080 \
  --dtype bfloat16 \
  --tensor-parallel-size 1 \
  --max-model-len 1024 \
  --gpu-memory-utilization 0.3
```

宿主机确认服务：

```bash
curl http://127.0.0.1:18080/v1/models
```

---

## 宿主机执行 benchmark

默认使用 image1：

```bash
python3 run_eval.py --config configs/images/h200_reuse_existing_service.json --judge-mode builtin --eval-mode quick
```

显式测试 image0：

```bash
python3 run_eval.py --config configs/images/image0_h200_reuse_existing_service.json --judge-mode builtin --eval-mode quick
```

显式测试 image1：

```bash
python3 run_eval.py --config configs/images/image1_h200_reuse_existing_service.json --judge-mode builtin --eval-mode quick
```

---

## 指标与结果文件

结果目录：

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
outputs/<run_id>/metrics.json
outputs/<run_id>/summary.json
outputs/<run_id>/report.md
outputs/<run_id>/final_brief.md
```

其中 `metrics.json` 提供当前版本的指标采集结果，包括：

- 吞吐峰值（RPS）
- 平均延迟 / P95 延迟
- 请求成功率
- 准确率代理（基于 builtin/api judge）
- 功能完备性代理（基于 smoke 成功率）
- 能效比采集状态（当前先标记为未接入）
