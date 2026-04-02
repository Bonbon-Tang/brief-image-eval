# H200 运行说明

## 目标环境

建议在真实 H200 机器上准备以下环境：

- Linux
- Docker
- NVIDIA Driver
- NVIDIA Container Toolkit
- Python 3.8+

## 基础检查

```bash
nvidia-smi
docker --version
python3 --version
```

## 安装 Python 依赖

```bash
cd brief-image-eval
pip3 install -r requirements.txt
```

## 准备评测 API

你需要提供一个可访问的 GPT-5.4 Judge API：

- API Base，例如：`https://api.mooko.ai/v1`
- API Key
- Judge Model，例如：`mooko/gpt-5.4`

## 执行示例

```bash
python3 run_eval.py \
  --config configs/images/qwen_vllm_example.json \
  --judge-api-base https://api.mooko.ai/v1 \
  --judge-api-key YOUR_KEY \
  --judge-model mooko/gpt-5.4
```

## 输出目录

结果默认写入：

```text
outputs/<run_id>/
```

包含：
- preflight.json
- launch.json
- smoke.json
- benchmark.json
- quality_samples.json
- judge_eval.json
- report.md

## 注意事项

1. 被测镜像需要能够在当前 H200 环境直接拉起
2. 如需挂载本地模型目录，可在镜像配置中扩展 docker 参数
3. 如 Judge API 不稳定，建议启用重试或在内网部署网关
