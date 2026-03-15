param(
  [string]$Backend = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

$file = "samples/complex_research/trace_agent_research.json"
if (-not (Test-Path $file)) { throw "Missing: $file" }

Write-Host "Ingest bundle: $file"
curl.exe -sS -X POST "$Backend/api/v1/ingest" -H "Content-Type: application/json" -d "@$file" | Write-Host

Write-Host "Done. Open UI and search trace_id: research_fullflow_000000000000000000000000000001"

