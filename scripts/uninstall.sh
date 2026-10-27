#!/usr/bin/env bash
# User-controlled uninstall. Personal voice profiles retained unless explicitly requested.
set -euo pipefail
DEST="${KOV_INSTALL_DIR:-$HOME/Library/Application Support/KeyboopOmniVoice/app}"
DELETE_PRIVATE=0
for arg in "$@"; do
  case "$arg" in
    --delete-private-data) DELETE_PRIVATE=1;;
    *) echo "Unknown option: $arg" >&2; exit 2;;
  esac
done
echo "Remove Keyboop + OmniVoice integration service and package?"
echo "The official Keyboop app is NOT removed."
if [[ -r /dev/tty ]]; then
  read -r -p "Continue? [y/N] " answer </dev/tty
else
  answer=""
fi
case "$answer" in y|Y|yes|YES) ;; *) echo "Cancelled"; exit 0;; esac
PLIST="$HOME/Library/LaunchAgents/dev.keyboop.omnivoice-kit.plist"
if [[ -f "$PLIST" ]]; then
  /bin/launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
  rm -f "$PLIST"
fi
if [[ -d "$DEST" ]]; then
  case "$DEST" in
    "$HOME/Library/Application Support/KeyboopOmniVoice/app" ) rm -rf "$DEST";;
    * ) echo "Refusing to delete unexpected installation path: $DEST" >&2; exit 1;;
  esac
fi
if [[ "$DELETE_PRIVATE" == 1 ]]; then
  echo "Permanently remove all voice recordings and downloaded model files?"
  read -r -p "Type DELETE to confirm: " answer </dev/tty
  if [[ "$answer" == "DELETE" ]]; then
    rm -rf "$HOME/.config/keyboop-omnivoice" "$HOME/.local/share/keyboop-omnivoice"
    echo "Local profiles, samples and model deleted."
  else
    echo "Private data retained."
  fi
else
  echo "Private voices and model retained in ~/.config/keyboop-omnivoice and ~/.local/share/keyboop-omnivoice."
fi
echo "The integration service has been removed."
