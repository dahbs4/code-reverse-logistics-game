#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm --prefix frontend ci --cache /tmp/reverse-npm-cache
npm --prefix frontend run build
