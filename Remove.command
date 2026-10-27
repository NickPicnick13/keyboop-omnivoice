#!/bin/bash
cd "$(dirname "$0")"
bash scripts/uninstall.sh "$@"
rc=$?
printf '\nНажми Enter, чтобы закрыть терминал.\n'
read -r _
exit "$rc"
