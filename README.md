# brief-image-eval

一个面向真实 H200 机器的镜像评测脚手架。

## 你的两个核心要求

1. **镜像必须真实存在且可以直接拉取**
2. **本地只启动一个脚本，就能执行完整流程**

这个项目已经按这两个要求设计：

- `image_uri` 必须由你明确填写为真实可拉取镜像
- preflight 阶段会强制执行 `docker pull`
- 提供统一启动脚本：`scripts/start_eval.sh`
- 评测支持三种模式：`quick / standard / deep`
- 流程结束后终端会直接打印 `final_brief.md` 的核心结论

## 完整流程

1. 读取镜像配置
2. 显式 `docker pull` 验证镜像真实可拉取
3. 执行 preflight 检查（docker / nvidia-smi / 镜像信息）
4. 启动被测推理服务
5. 执行 smoke test
6. 执行 benchmark
7. 按评测模式执行 quality samples
8. 调用外部 Judge API，对质量样例进行分析与总结
9. 生成 summary.json / report.md / final_brief.md
10. 清理容器
11. 在终端直接打印最终摘要

## 本地一键启动

### 第一步：准备环境变量

```bash
cd /home/admin/.openclaw/workspace/brief-image-eval
cp .env.example .env
```

编辑 `.env`，至少填写：

```bash
JUDGE_API_BASE=https://api.mooko.ai/v1
JUDGE_API_KEY=YOUR_API_KEY
JUDGE_MODEL=mooko/gpt-5.4
EVAL_MODE=quick
IMAGE_CONFIG=configs/images/qwen_vllm_example.json
```

### 第二步：填写真实镜像地址

编辑：

```bash
configs/images/qwen_vllm_example.json
```

把：

```json
"image_uri": "YOUR_REAL_PULLABLE_IMAGE_URI"
```

替换成真实可拉取镜像地址。

建议先手动验证：

```bash
docker pull <your_image_uri>
```

### 第三步：一键执行

```bash
bash scripts/start_eval.sh
```

## 评测模式

- `quick`：快速检查，适合先看镜像是否基本可用
- `standard`：标准评测，适合日常工程验证
- `deep`：深度评测，适合更完整地给出风险与建议

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
- quality_samples.json
- judge_eval_raw.json
- judge_eval.json
- summary.json
- report.md
- final_brief.md

其中：
- `report.md`：完整报告
- `final_brief.md`：用户更容易快速阅读的摘要结论
- 终端执行完成后也会直接打印 `final_brief.md`

## 文档

- `configs/images/README.md`
- `docs/H200_RUN_GUIDE.md`
- `docs/PROJECT_START_GUIDE.md`
