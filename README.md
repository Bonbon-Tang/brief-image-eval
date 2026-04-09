# brief-image-eval

一个面向真实 GPU 机器的镜像评测脚手架。

当前采用 **方案 B**：

- **开发机联网**，负责拉基础镜像、准备小模型、导出离线镜像包
- **H200 不拉镜像**，只接收 `docker save` 导出的 tar.gz，然后 `docker load` + `docker run`

目标是先用一个小模型把 **离线镜像交付 → H200 执行 benchmark → 输出结果** 这条链路跑通。

---

## 一、开发机需要执行的全部命令

### 1. 拉代码

```bash
git clone https://github.com/Bonbon-Tang/brief-image-eval.git
cd brief-image-eval
```

### 2. 给脚本执行权限

```bash
chmod +x scripts/build_offline_image.sh scripts/run_h200_benchmark.sh
```

### 3. 构建离线被测镜像（小模型）

默认会使用：

- 基础镜像：`vllm/vllm-openai:latest`
- 模型：`Qwen/Qwen2.5-0.5B-Instruct`
- 目标镜像名：`brief-image-eval-qwen25-0p5b-vllm:offline`

执行：

```bash
bash scripts/build_offline_image.sh
```

如果想显式写全参数，也可以：

```bash
IMAGE_NAME=brief-image-eval-qwen25-0p5b-vllm:offline \
BASE_IMAGE=vllm/vllm-openai:latest \
MODEL_ID=Qwen/Qwen2.5-0.5B-Instruct \
HF_CACHE_DIR=$HOME/.cache/huggingface \
bash scripts/build_offline_image.sh
```

### 4. 导出离线镜像包

```bash
docker save brief-image-eval-qwen25-0p5b-vllm:offline | gzip > brief-image-eval-qwen25-0p5b-vllm-offline.tar.gz
```

### 5. 传代码目录到 H200

```bash
scp -r brief-image-eval <user>@<h200-host>:/path/to/
```

### 6. 传离线镜像包到 H200

```bash
scp brief-image-eval-qwen25-0p5b-vllm-offline.tar.gz <user>@<h200-host>:/path/to/
```

---

## 二、H200 需要执行的全部命令

### 1. 基础检查

```bash
nvidia-smi
docker --version
python3 --version
```

### 2. 进入项目目录

```bash
cd /path/to/brief-image-eval
```

### 3. 安装 Python 依赖

```bash
pip3 install -r requirements.txt
```

### 4. 导入开发机传来的离线镜像包

```bash
gunzip -c /path/to/brief-image-eval-qwen25-0p5b-vllm-offline.tar.gz | docker load
```

### 5. 确认本地镜像存在

```bash
docker images | grep brief-image-eval-qwen25-0p5b-vllm
```

### 6. 执行 benchmark

项目已经提供了离线配置：

- `configs/images/h200_offline_qwen25_0p5b_vllm.json`

直接执行：

```bash
python3 run_eval.py \
  --config configs/images/h200_offline_qwen25_0p5b_vllm.json \
  --judge-mode builtin \
  --eval-mode quick
```

或者用脚本执行：

```bash
IMAGE_CONFIG=configs/images/h200_offline_qwen25_0p5b_vllm.json \
JUDGE_MODE=builtin \
EVAL_MODE=quick \
bash scripts/run_h200_benchmark.sh
```

---

## 三、当前离线配置说明

离线配置文件：

```text
configs/images/h200_offline_qwen25_0p5b_vllm.json
```

核心约束：

- `image_uri = brief-image-eval-qwen25-0p5b-vllm:offline`
- `model_id = Qwen/Qwen2.5-0.5B-Instruct`
- `offline_image_only = true`

这表示在 H200 上：

- **不会执行 `docker pull`**
- 只会检查本地镜像是否存在
- 本地没有该镜像就直接报错

---

## 四、输出结果

结果默认写入：

```text
outputs/<run_id>/
```

重点关注这些文件：

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

查看最近一次结果可以手动进入 `outputs/` 目录查看。

---

## 五、推荐首次验收标准

第一次只验收这几件事：

1. H200 上 `docker load` 成功
2. `preflight.json` 显示通过，并且没有发生 `docker pull`
3. 容器成功拉起
4. `smoke + benchmark + quality` 执行完成
5. `outputs/<run_id>/` 成功生成结果文件

只要这几项都成立，就说明 **方案 B 的离线链路已经跑通**。
