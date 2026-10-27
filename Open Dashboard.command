#!/bin/bash
set -e
PORT="${KOV_PORT:-3912}"
if ! /usr/bin/curl --noproxy '*' -fsS --max-time 3 "http://127.0.0.1:$PORT/health" >/dev/null; then
  echo "Локальный голосовой сервер не запущен. Сначала запусти Install.command."
  read -r -p "Нажми Enter для выхода..." _
  exit 1
fi
/usr/bin/open "http://127.0.0.1:$PORT/"
