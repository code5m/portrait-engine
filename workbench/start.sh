#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
PYTHON=${PYTHON:-python3}
if [ ! -x .venv-workbench/bin/python ]; then "$PYTHON" -m venv .venv-workbench; fi
.venv-workbench/bin/python -m pip install -r workbench/requirements.txt
.venv-workbench/bin/python -m playwright install chromium
if ! command -v blender >/dev/null 2>&1; then
  printf '%s\n' 'Blender is missing: rendering and human review work; independent machine verification needs Blender.' 'Ubuntu: sudo apt-get install blender'
fi
exec .venv-workbench/bin/python workbench/server.py "$@"
