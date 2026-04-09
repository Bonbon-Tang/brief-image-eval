#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

IMAGE_CONFIG="${IMAGE_CONFIG:-configs/images/h200_qwen25_3b_vllm.json}"
EVAL_MODE="${EVAL_MODE:-quick}"
JUDGE_MODE="${JUDGE_MODE:-builtin}"
JUDGE_API_BASE="${JUDGE_API_BASE:-}"
JUDGE_API_KEY="${JUDGE_API_KEY:-}"
JUDGE_MODEL="${JUDGE_MODEL:-mooko/gpt-5.4}"
KEEP_CONTAINER="${KEEP_CONTAINER:-false}"

cmd=(
  python3 run_eval.py
  --config "$IMAGE_CONFIG"
  --eval-mode "$EVAL_MODE"
  --judge-mode "$JUDGE_MODE"
  --judge-api-base "$JUDGE_API_BASE"
  --judge-api-key "$JUDGE_API_KEY"
  --judge-model "$JUDGE_MODEL"
)

if [[ "$KEEP_CONTAINER" == "true" ]]; then
  cmd+=(--keep-container)
fi

echo "[INFO] running H200 benchmark pipeline"
echo "[INFO] config=$IMAGE_CONFIG"
echo "[INFO] eval_mode=$EVAL_MODE"
echo "[INFO] judge_mode=$JUDGE_MODE"
echo "[INFO] keep_container=$KEEP_CONTAINER"

run_name="$(basename "$IMAGE_CONFIG" .json)_${EVAL_MODE}_$(date +%Y%m%d_%H%M%S)"
log_dir="outputs/_logs/${run_name}"
mkdir -p "$log_dir"
log_file="$log_dir/output.log"

echo "[INFO] bootstrap_log_dir=$log_dir"
echo "[INFO] bootstrap_output_log=$log_file"

"${cmd[@]}" 2>&1 | tee "$log_file"
