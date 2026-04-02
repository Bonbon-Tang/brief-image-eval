#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

IMAGE_CONFIG="${IMAGE_CONFIG:-configs/images/qwen_vllm_example.json}"
JUDGE_API_BASE="${JUDGE_API_BASE:-}"
JUDGE_API_KEY="${JUDGE_API_KEY:-}"
JUDGE_MODEL="${JUDGE_MODEL:-mooko/gpt-5.4}"
EVAL_MODE="${EVAL_MODE:-quick}"

if [[ -z "$JUDGE_API_BASE" || -z "$JUDGE_API_KEY" ]]; then
  echo "[ERROR] missing JUDGE_API_BASE or JUDGE_API_KEY"
  echo "Please copy .env.example to .env and fill in the values."
  exit 1
fi

echo "[INFO] starting full evaluation workflow"
echo "[INFO] config=$IMAGE_CONFIG"
echo "[INFO] eval_mode=$EVAL_MODE"

python3 run_eval.py \
  --config "$IMAGE_CONFIG" \
  --judge-api-base "$JUDGE_API_BASE" \
  --judge-api-key "$JUDGE_API_KEY" \
  --judge-model "$JUDGE_MODEL" \
  --eval-mode "$EVAL_MODE"
