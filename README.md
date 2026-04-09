# brief-image-eval

一个面向真实 GPU 机器的镜像评测脚手架。

当前仓库主路径已经切换为：**复用 H200 上已有服务**。

适用场景：

- H200 上已经有一个正在运行的 OpenAI 兼容模型服务
- 当前机器不方便联网拉模型
- 当前阶段目标是先把 **服务复用 → benchmark runner → 输出结果** 这条链路稳定跑通

> 重要：`run_eval.py` 要在 **H200 宿主机** 执行，不要在被测 vLLM 容器里执行。

---

## 一、当前默认配置

默认使用：

- 容器名：`caikun-dlrouter`
- 服务地址：`http://127.0.0.1:18080`
- 镜像：`registry.h.pjlab.org.cn/ailab-sys/vllm:v0.17.1`
- 配置文件：`configs/images/h200_reuse_existing_service.json`
- 评测模式：`builtin + quick`

配置文件内容核心如下：

```json
{
  "reuse_existing_service": true,
  "existing_container_name": "caikun-dlrouter",
  "base_url": "http://127.0.0.1:18080"
}
```

这意味着：

- 不会 `docker pull`
- 不会新起容器
- 不会 cleanup 容器
- 只会直接请求已有服务做 smoke / benchmark / quality

---

## 二、H200 直接执行命令

### 1. 先确认已有服务可访问

```bash
curl http://127.0.0.1:18080/v1/models
```

只要这条能返回 JSON，就说明可以继续。

如果这条不通，请先检查已有容器的实际端口：

```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}' | grep caikun-dlrouter
```

如果端口不是 `18080`，请同步修改：

```text
configs/images/h200_reuse_existing_service.json
```

里的 `base_url`。

### 2. 进入项目目录

```bash
cd /mnt/nvme1n1/tangyufeng/brief-image-eval
```

### 3. 安装 Python 依赖

```bash
pip3 install -r requirements.txt
```

### 4. 执行 benchmark

```bash
python3 run_eval.py \
  --config configs/images/h200_reuse_existing_service.json \
  --judge-mode builtin \
  --eval-mode quick
```

或者用脚本执行：

```bash
IMAGE_CONFIG=configs/images/h200_reuse_existing_service.json \
JUDGE_MODE=builtin \
EVAL_MODE=quick \
bash scripts/run_h200_benchmark.sh
```

---

## 三、输出结果

结果默认写入：

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

## 四、当前建议

当前目标是 **方向 A：先确认链路稳定可复现**。

所以判断成功的标准不是先追求高分，而是：

1. 已有服务可访问
2. runner 可以完整跑完
3. `outputs/<run_id>/` 能稳定生成结果

如果结果是 `FAIL`，但流程完整走通，也说明这条工程链已经打通。
后续再处理模型效果、失败样例、并发稳定性等问题。
