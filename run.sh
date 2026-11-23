#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
python=python3
if [[ -x .venv/bin/python ]]; then python=.venv/bin/python; fi
exec "$python" -m valvula "$@"
