#!/bin/bash
# Double-click after extracting the GitHub release ZIP on a Mac.
cd "$(dirname "$0")"
bash scripts/install.sh "$@"
rc=$?
if [[ "$rc" != 0 ]]; then echo "Установка завершилась с ошибкой (код $rc). Сообщение выше объясняет причину."; fi
printf '\nНажми Enter, чтобы закрыть терминал.\n'
read -r _
exit "$rc"
