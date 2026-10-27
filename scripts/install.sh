#!/usr/bin/env bash
# First-run package installation; does not touch any existing TTS services.
set -euo pipefail

SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${KOV_INSTALL_DIR:-$HOME/Library/Application Support/KeyboopOmniVoice/app}"
PORT="${KOV_PORT:-3912}"
DRY_RUN=0
SKIP_KEYBOOP=0
SKIP_MODEL=0
NO_SERVICE=0
NO_OPEN=0
ACCEPT_LICENSE=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1;;
    --skip-keyboop) SKIP_KEYBOOP=1;;
    --skip-model) SKIP_MODEL=1;;
    --no-service) NO_SERVICE=1;;
    --no-open) NO_OPEN=1;;
    --accept-noncommercial-license) ACCEPT_LICENSE=1;;
    *) printf 'Unknown option: %s\n' "$arg" >&2; exit 2;;
  esac
done

info() { printf '\n== %s ==\n' "$1"; }
fail() { printf '\nERROR: %s\n' "$1" >&2; exit 1; }
if [[ "$DRY_RUN" == 1 ]]; then
  printf '%s\n' "Dry run: Apple Silicon preflight → copy to user Application Support → install Python 3.11 and OmniVoice via uv → verified Keyboop DMG → download CC-BY-NC model with consent → install login service → open dashboard."
  printf 'No changes made. Target: %s; service: 127.0.0.1:%s\n' "$DEST" "$PORT"
  exit 0
fi
[[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]] || fail "OmniVoice requires an Apple Silicon Mac (M1 or newer). Keyboop is available separately for Intel Macs."
[[ "$PORT" =~ ^[0-9]+$ ]] && (( PORT >= 1024 && PORT <= 65535 )) || fail "Invalid KOV_PORT"
MAC_MAJOR="$(sw_vers -productVersion | cut -d. -f1)"
(( MAC_MAJOR >= 14 )) || fail "This installer requires macOS 14 or newer."

info "Keyboop + OmniVoice · macOS installer"
echo "Installs only in your user account. No admin password is needed."
echo "OmniVoice weights require approximately 3.3 GB of free space, plus dependencies."
echo "Voice cloning is permitted only with the voice owner's consent."

if [[ "$SKIP_MODEL" == 0 && "$ACCEPT_LICENSE" == 0 ]]; then
  echo ""
  echo "MODEL TERMS: OmniVoice source code is Apache-2.0, but official model weights"
  echo "are CC-BY-NC (noncommercial use only). The model may not be used for"
  echo "unauthorized impersonation, deception or cloning without consent."
  if [[ -r /dev/tty ]]; then
    read -r -p "Accept these restrictions and download the model? [y/N] " answer </dev/tty
  else
    answer=""
  fi
  case "$answer" in y|Y|yes|YES) ACCEPT_LICENSE=1;; *) fail "Model license not accepted; installation stopped before making changes.";; esac
fi

if [[ "$SOURCE" != "$DEST" ]]; then
  info "Copying package to permanent user installation"
  mkdir -p "$DEST"
  /usr/bin/rsync -a \
    --exclude '.git/' --exclude '.venv/' --exclude '.pytest_cache/' \
    --exclude '__pycache__/' --exclude '*.egg-info/' --exclude 'tests/' \
    --exclude '.DS_Store' --exclude 'dist/' \
    "$SOURCE/" "$DEST/"
fi
cd "$DEST"

info "Installing Python toolchain"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "Installing uv using Homebrew"
    brew install uv
  else
    echo "Homebrew not found. Installing uv from the official Astral bootstrap."
    echo "Source: https://astral.sh/uv/install.sh"
    curl -LsSf --retry 3 https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  fi
fi
command -v uv >/dev/null 2>&1 || fail "Could not install uv"
uv python install 3.11
if [[ ! -x ".venv/bin/python" ]]; then
  uv venv --python 3.11 .venv
fi
uv pip install --python ".venv/bin/python" -e ".[runtime]"

if [[ "$SKIP_KEYBOOP" == 0 ]]; then
  info "Installing the original, signed Keyboop app"
  echo "Official developer release; no third-party modifications to Keyboop."
  .venv/bin/keyboop-omnivoice install-keyboop
fi

if [[ "$SKIP_MODEL" == 0 ]]; then
  info "Downloading OmniVoice pretrained weights (noncommercial license)"
  .venv/bin/keyboop-omnivoice download-model --accept-noncommercial-license
fi
info "Creating a starter voice and checking the setup"
.venv/bin/keyboop-omnivoice bootstrap
.venv/bin/keyboop-omnivoice doctor

if [[ "$NO_SERVICE" == 0 ]]; then
  info "Enabling voice API at login"
  if /usr/sbin/lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    if ! /usr/bin/grep -q '<string>dev.keyboop.omnivoice-kit</string>' \
      "$HOME/Library/LaunchAgents/dev.keyboop.omnivoice-kit.plist" 2>/dev/null; then
      fail "Port $PORT is used by another service. No processes were stopped."
    fi
  fi
  .venv/bin/keyboop-omnivoice service install --port "$PORT"
  if [[ "$NO_OPEN" == 0 ]]; then
    for _ in $(seq 1 20); do
      if /usr/bin/curl --noproxy '*' -fsS --max-time 2 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
        /usr/bin/open "http://127.0.0.1:$PORT/"
        break
      fi
      sleep 1
    done
  fi
fi
info "Installation complete"
echo "Control panel: http://127.0.0.1:$PORT/"
echo "The default narrator voice is ready to try after the model loads."
echo "Add an authorized reference WAV in the panel to clone a real voice."
echo "Keyboop keyboard permissions must be granted manually in macOS System Settings."
echo "To remove the service, run Remove.command from this package."
