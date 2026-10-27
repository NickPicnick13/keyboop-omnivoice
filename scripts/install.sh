#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != "Darwin" ]] || [[ "$(uname -m)" != "arm64" ]]; then
  echo "OmniVoice MPS installer requires Apple Silicon macOS. Keyboop can be installed separately." >&2
  exit 1
fi
if ! command -v python3.11 >/dev/null; then
  echo "Python 3.11 is required. Install it using Homebrew (brew install python@3.11) or python.org." >&2
  exit 1
fi
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[runtime]"
echo "Installation finished. Download OmniVoice weights using official upstream instructions."
echo 'Set KOV_MODEL_DIR=/path/to/model, run source .venv/bin/activate; keyboop-omnivoice doctor'
echo 'Then add a consented voice and run: keyboop-omnivoice serve'
