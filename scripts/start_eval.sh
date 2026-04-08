#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

IMAGE_CONFIG="${IMAGE_CONFIG:-configs/images/h200_qwen25_3b_vllm.json}"
JUDGE_MODE="${JUDGE_MODE:-builtin}"
JUDGE_API_BASE="${JUDGE_API_BASE:-}"
JUDGE_API_KEY="${JUDGE_API_KEY:-}"
JUDGE_MODEL="${JUDGE_MODEL:-mooko/gpt-5.4}"
EVAL_MODE="${EVAL_MODE:-quick}"

if [[ "$JUDGE_MODE" == "api" ]]; then
  if [[ -z "$JUDGE_API_BASE" || -z "$JUDGE_API_KEY" ]]; then
    echo "[ERROR] judge_mode=api but missing JUDGE_API_BASE or JUDGE_API_KEY"
    echo "Please copy .env.example to .env and fill in the values."
    exit 1
  fi
fi

echo "[INFO] starting full evaluation workflow"
echo "[INFO] config=$IMAGE_CONFIG"
echo "[INFO] eval_mode=$EVAL_MODE"
echo "[INFO] judge_mode=$JUDGE_MODE"

python3 run_eval.py \
  --config "$IMAGE_CONFIG" \
  --judge-mode "$JUDGE_MODE" \
  --judge-api-base "$JUDGE_API_BASE" \
  --judge-api-key "$JUDGE_API_KEY" \
  --judge-model "$JUDGE_MODEL" \
  --eval-mode "$EVAL_MODE"
