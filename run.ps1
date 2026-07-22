param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Virtual environment not found. Create .venv and install requirements-dev.txt first."
}

& $python -m uvicorn app.main:app --host 127.0.0.1 --port $Port --reload

