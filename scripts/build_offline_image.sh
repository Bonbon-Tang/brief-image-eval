#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-brief-image-eval-qwen25-0p5b-vllm:offline}"
BASE_IMAGE="${BASE_IMAGE:-vllm/vllm-openai:latest}"
MODEL_ID="${MODEL_ID:-Qwen/Qwen2.5-0.5B-Instruct}"
HF_CACHE_DIR="${HF_CACHE_DIR:-$HOME/.cache/huggingface}"

mkdir -p "$HF_CACHE_DIR"

echo "[INFO] pulling base image: $BASE_IMAGE"
docker pull "$BASE_IMAGE"

echo "[INFO] warming model cache: $MODEL_ID"
docker run --rm --gpus all \
  -v "$HF_CACHE_DIR:/root/.cache/huggingface" \
  --ipc=host \
  "$BASE_IMAGE" \
  python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='$MODEL_ID')"

echo "[INFO] committing offline image: $IMAGE_NAME"
CID=$(docker create \
  --gpus all \
  -v "$HF_CACHE_DIR:/root/.cache/huggingface" \
  --ipc=host \
  "$BASE_IMAGE" \
  bash -lc "python -c \"from huggingface_hub import snapshot_download; snapshot_download(repo_id='$MODEL_ID')\" >/tmp/model_warmup.log 2>&1 || (cat /tmp/model_warmup.log && exit 1) && cp -a /root/.cache/huggingface /opt/hf-cache")

docker start -a "$CID"
docker commit "$CID" "$IMAGE_NAME" >/dev/null
docker rm "$CID" >/dev/null

echo "[INFO] image ready: $IMAGE_NAME"
echo "[INFO] export with: docker save $IMAGE_NAME | gzip > brief-image-eval-qwen25-0p5b-vllm-offline.tar.gz"
