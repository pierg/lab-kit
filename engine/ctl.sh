#!/usr/bin/env bash
# Start / stop / status a lab's reader server (stdlib serve.py, background).
set -euo pipefail
KIT="$(cd "$(dirname "$0")/.." && pwd)"
LAB_ROOT="${LAB_ROOT:-$(cd "$KIT/.." && pwd)}"
export LAB_ROOT
cd "$LAB_ROOT"

PIDFILE="${PIDFILE:-.serve.pid}"
LOGFILE="${LOGFILE:-.serve.log}"

# Match this lab's server only — several labs serve concurrently on different ports.
_serve_pids() {
  pgrep -f "python3 .*engine/serve[.]py.*--lab-root ${LAB_ROOT}\$" 2>/dev/null || \
  { [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null && cat "$PIDFILE"; } || true
}

_url() {
  python3 - <<'PY'
import json, os, pathlib
cfg = {"host": "127.0.0.1", "port": 5180}
p = pathlib.Path(os.environ["LAB_ROOT"]) / "lab.json"
if p.is_file():
    cfg.update(json.loads(p.read_text()))
print(f"http://{os.environ.get('HOST', cfg['host'])}:{os.environ.get('PORT', cfg['port'])}/")
PY
}

start() {
  local pids; pids="$(_serve_pids)"
  if [ -n "$pids" ]; then echo "already running at $(_url)  (pid ${pids})"; return 0; fi
  rm -f "$PIDFILE"
  local args=()
  [ -n "${HOST:-}" ] && args+=(--host "$HOST")
  [ -n "${PORT:-}" ] && args+=(--port "$PORT")
  # shellcheck disable=SC2086
  python3 "$KIT/engine/serve.py" --lab-root "$LAB_ROOT" ${args[@]+"${args[@]}"} >"$LOGFILE" 2>&1 &
  echo $! >"$PIDFILE"
  sleep 0.3
  if ! kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "failed to start — see ${LOGFILE}" >&2; rm -f "$PIDFILE"; return 1
  fi
  echo "serving $(_url)  (pid $(cat "$PIDFILE"); make down to stop)"
}

stop() {
  local pids; pids="$(_serve_pids)"
  # shellcheck disable=SC2086
  if [ -n "$pids" ]; then echo "stopping ${pids}"; kill $pids 2>/dev/null || true
  else echo "not running"; fi
  rm -f "$PIDFILE"
}

status() {
  local pids; pids="$(_serve_pids)"
  if [ -n "$pids" ]; then echo "running at $(_url)  (pid ${pids})"; else echo "not running"; return 1; fi
}

case "${1:-}" in
  start|stop|status) "$1" ;;
  *) echo "usage: $0 start|stop|status" >&2; exit 2 ;;
esac
