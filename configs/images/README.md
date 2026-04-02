# 镜像配置说明

## 重要要求

`image_uri` 必须是**真实存在且可以直接 docker pull 的镜像地址**。

本项目不会依赖一个“示意镜像名”来默认运行，而是要求你明确填写一个已经验证存在的镜像地址。
随后流程会在 preflight 阶段强制执行：

```bash
docker pull <image_uri>
```

如果拉取失败，整个流程直接失败。

## 示例字段

- `name`: 本次评测任务名称
- `image_uri`: 真实可拉取镜像地址
- `model_id`: 模型名，例如 `Qwen/Qwen2.5-7B-Instruct`
- `source_url`: 镜像来源页面
- `trust_level`: `official` / `vendor` / `community` / `verified`

## 建议

在正式跑之前，先手动验证一次：

```bash
docker pull <image_uri>
```
