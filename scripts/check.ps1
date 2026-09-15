# ClarityKit Full Foundation Quality & Test Runner
$ErrorActionPreference = "Stop"

Write-Host "=== Running Backend Quality Checks & Tests ===" -ForegroundColor Cyan
Push-Location "backend"
try {
    & .venv\Scripts\ruff check .
    & .venv\Scripts\ruff format --check .
    & .venv\Scripts\mypy app
    & .venv\Scripts\pytest
} finally {
    Pop-Location
}

Write-Host "=== Running Frontend Quality Checks, Tests & Build ===" -ForegroundColor Cyan
Push-Location "frontend"
try {
    & npm run format:check
    & npm run lint
    & npm run typecheck
    & npm run test
    & npm run build
} finally {
    Pop-Location
}

Write-Host "=== All ClarityKit Foundation Quality Checks Passed! ===" -ForegroundColor Green
