param(
  [string]$Backend = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

Write-Host "Step1: span without output (start/input/attributes)"
curl.exe -sS -X POST "$Backend/api/v1/ingest/span" -H "Content-Type: application/json" -d "@samples/distributed/partial_update_demo_step1.json" | Write-Host
Start-Sleep -Milliseconds 200
Write-Host "Step2: same span_id update with end/output only (should NOT erase previous fields)"
curl.exe -sS -X POST "$Backend/api/v1/ingest/span" -H "Content-Type: application/json" -d "@samples/distributed/partial_update_demo_step2.json" | Write-Host

Write-Host "Done. Open UI and search trace_id: partial_update_demo_000000000000000000000000000001"

