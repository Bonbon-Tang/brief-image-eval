# brief-image-eval

一个面向真实 H200 机器的镜像评测脚手架。

## 设计目标

- **统一入口**：通过单一入口文件一键执行完整流程
- **独立运行**：可直接部署在真实 H200 机器，不依赖 OpenClaw 子 agent
- **API 驱动评测**：评测阶段通过外部大模型 API（如 GPT-5.4）完成质量分析、风险识别与结论生成
- **可扩展**：后续输出可对接 ai-eval-platform

## 流程

1. 读取镜像配置
2. 执行 preflight 检查（docker / nvidia-smi / 镜像信息）
3. 启动被测推理服务
4. 执行 smoke test
5. 执行 benchmark
6. 调用外部评测 API，对质量样例进行分析与总结
7. 生成 summary.json 与 report.md
8. 清理容器

## 一键执行

```bash
cd /home/admin/.openclaw/workspace/brief-image-eval
python3 run_eval.py \
  --config configs/images/qwen_vllm_example.json \
  --judge-api-base https://api.mooko.ai/v1 \
  --judge-api-key YOUR_KEY \
  --judge-model mooko/gpt-5.4
```

或：

```bash
bash scripts/eval_one.sh configs/images/qwen_vllm_example.json https://api.mooko.ai/v1 YOUR_KEY mooko/gpt-5.4
```

## 输出

所有结果写入：

```text
outputs/<run_id>/
```

包含：
- meta.json
- preflight.json
- launch.json
- smoke.json
- benchmark.json
- judge_eval.json
- summary.json
- report.md

## 说明

- 第一版默认支持 vLLM OpenAI 兼容服务
- 评测 API 采用 OpenAI-compatible Chat Completions 方式调用
- 后续可扩展为 Responses API、平台回传、更多镜像模板
