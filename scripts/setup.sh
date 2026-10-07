#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ required"'
python3 -m venv .venv
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$PWD/data/pip-cache}"
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.lock
.venv/bin/python -c 'from defuse.render import ffmpeg_binary; print("ffmpeg:", ffmpeg_binary())'
printf '%s\n' 'Setup complete. Activate with: source .venv/bin/activate' 'Then run: python -m defuse.doctor'
