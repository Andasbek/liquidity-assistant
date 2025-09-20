#!/usr/bin/env bash
set -euo pipefail

API="${API_BASE:-http://localhost:8000/api}"
H="${HORIZON_DAYS:-14}"
ROLE_ANALYST="${ROLE_ANALYST:-Analyst}"
ROLE_CFO="${ROLE_CFO:-CFO}"

curl -s -X POST -H "X-Role: $ROLE_ANALYST" "$API/dev/seed" >/dev/null || true

FC=$(curl -s -X POST -H "Content-Type: application/json" -H "X-Role: $ROLE_ANALYST" \
  -d "{\"horizon_days\":$H}" "$API/forecast")

SC=$(curl -s -X POST -H "Content-Type: application/json" -H "X-Role: $ROLE_ANALYST" \
  -d "{\"horizon_days\":$H,\"scenario\":\"stress\",\"fx_shock\":0.1}" "$API/scenario")

AD=$(jq -n --argjson b "$FC" --argjson s "$SC" '{baseline:$b, scenario:$s}')
ADV=$(curl -s -X POST -H "Content-Type: application/json" -H "X-Role: $ROLE_CFO" \
  -d "$AD" "$API/advice")

PDF_PAYLOAD=$(jq -n --argjson b "$FC" --argjson s "$SC" --argjson a "$ADV" \
  --argjson h "$H" '{baseline:$b,scenario:$s,advice:$a,horizon_days:($h|tonumber)}')

curl -s -X POST -H "Content-Type: application/json" -H "X-Role: $ROLE_CFO" \
  -d "$PDF_PAYLOAD" "$API/report/pdf" > liquidity_brief.pdf

# вывести base64 (часто нужно для «файла» в оркестраторе)
b64=$(base64 -i liquidity_brief.pdf)
echo "{\"pdf_base64\":\"$b64\"}"
