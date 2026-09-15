#!/usr/bin/env bash
set -e

echo "=== Running Backend Quality Checks & Tests ==="
cd backend
python -m ruff check .
python -m ruff format --check .
python -m mypy app
python -m pytest
cd ..

echo "=== Running Frontend Quality Checks, Tests & Build ==="
cd frontend
npm run format:check
npm run lint
npm run typecheck
npm run test
npm run build
cd ..

echo "=== All ClarityKit Foundation Quality Checks Passed! ==="
