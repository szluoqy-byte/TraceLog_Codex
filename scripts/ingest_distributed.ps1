param(
  [string]$Backend = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

$files = @(
  "samples/distributed/span_node_b_llm_final.json",
  "samples/distributed/span_node_a.json",
  "samples/distributed/span_node_a_tool.json",
  "samples/distributed/span_node_b_llm.json"
)

foreach ($f in $files) {
  if (-not (Test-Path $f)) { throw "Missing: $f" }
  Write-Host "Ingest span: $f"
  curl.exe -sS -X POST "$Backend/api/v1/ingest/span" -H "Content-Type: application/json" -d "@$f" | Write-Host
}

Write-Host "Done. Open UI and search trace_id: d1str1buted4bf34da6a3ce929d0e0e111"

