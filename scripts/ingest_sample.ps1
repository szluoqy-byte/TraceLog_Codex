param(
  [string]$Backend = "http://127.0.0.1:8000",
  [string]$Sample = "samples/trace_sample.json"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Sample)) {
  throw "Sample not found: $Sample"
}

Write-Host "Ingesting $Sample -> $Backend/api/v1/ingest"
curl.exe -sS -X POST "$Backend/api/v1/ingest" -H "Content-Type: application/json" -d "@$Sample" | Write-Host

