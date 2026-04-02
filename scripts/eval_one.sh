#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
CONFIG="${1:-configs/images/qwen_vllm_example.json}"
JUDGE_API_BASE="${2:-}"
JUDGE_API_KEY="${3:-}"
JUDGE_MODEL="${4:-mooko/gpt-5.4}"

if [[ -z "$JUDGE_API_BASE" || -z "$JUDGE_API_KEY" ]]; then
  echo "Usage: bash scripts/eval_one.sh <config> <judge_api_base> <judge_api_key> [judge_model]"
  exit 1
fi

python3 run_eval.py \
  --config "$CONFIG" \
  --judge-api-base "$JUDGE_API_BASE" \
  --judge-api-key "$JUDGE_API_KEY" \
  --judge-model "$JUDGE_MODEL"
