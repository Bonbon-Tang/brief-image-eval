#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-18000}"
docker rm -f "eval_${PORT}" >/dev/null 2>&1 || true
echo "cleanup done for eval_${PORT}"
