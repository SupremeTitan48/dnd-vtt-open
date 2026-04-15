#!/usr/bin/env bash
set -euo pipefail
.venv/bin/python -m ruff check .
.venv/bin/pytest
