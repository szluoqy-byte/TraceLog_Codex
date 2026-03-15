param(
  [string]$Backend = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

# Simulate distributed nodes ingesting out of order.
$files = @(
  "samples/distributed_graph/span_D_from_C.json",
  "samples/distributed_graph/span_B.json",
  "samples/distributed_graph/span_A.json",
  "samples/distributed_graph/span_E_from_C.json",
  "samples/distributed_graph/span_D_from_A.json",
  "samples/distributed_graph/span_C.json"
)

foreach ($f in $files) {
  if (-not (Test-Path $f)) { throw "Missing: $f" }
  Write-Host "Ingest span: $f"
  curl.exe -sS -X POST "$Backend/api/v1/ingest/span" -H "Content-Type: application/json" -d "@$f" | Write-Host
}

Write-Host "Done. Open UI and search trace_id: graph_fanout_000000000000000000000000000001"

