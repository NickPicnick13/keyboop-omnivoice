#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VERSION="0.2.0-beta.1"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Commit and verify all changes before packaging" >&2
  exit 1
fi
OUT="$ROOT/dist/Keyboop-OmniVoice-v$VERSION-macOS.zip"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/Keyboop-OmniVoice" "$ROOT/dist"
git archive --format=tar HEAD | tar -xf - -C "$TMP/Keyboop-OmniVoice"
(
  cd "$TMP"
  /usr/bin/zip -q -r -X "$OUT" "Keyboop-OmniVoice"
)
/usr/bin/unzip -t "$OUT" | tail -1
shasum -a 256 "$OUT"
echo "Release asset: $OUT"
