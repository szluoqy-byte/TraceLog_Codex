#!/usr/bin/env bash
set -euo pipefail

BACKEND="${1:-http://127.0.0.1:8000}"
SAMPLE="${2:-samples/trace_sample.json}"

curl -sS -X POST "$BACKEND/api/v1/ingest" \
  -H "Content-Type: application/json" \
  --data-binary "@$SAMPLE"
echo

