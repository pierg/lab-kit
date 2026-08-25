#!/usr/bin/env bash
# Confirm the vendored kit still matches its pin — or re-sync it deliberately.
#
#   bash kit/verify.sh          # verify (used by `make check`)
#   bash kit/verify.sh --sync   # re-vendor from the pinned source
set -euo pipefail
KIT="$(cd "$(dirname "$0")" && pwd)"
LAB="$(cd "$KIT/.." && pwd)"

[ -f "$KIT/PIN" ] || { echo "kit: no PIN file — this kit was not installed by install.sh" >&2; exit 1; }
SRC="$(awk '/^source/ {print $2}' "$KIT/PIN")"
PINNED="$(awk '/^hash/ {print $2}' "$KIT/PIN")"

if [ "${1:-}" = "--sync" ]; then
  [ -d "$SRC" ] || { echo "kit: source $SRC not present — cannot sync" >&2; exit 1; }
  echo "re-vendoring from $SRC"
  bash "$SRC/install.sh" "$LAB"
  exit 0
fi

ACTUAL="$(python3 "$KIT/tools/kit_hash.py" "$KIT")"
if [ "$ACTUAL" != "$PINNED" ]; then
  cat >&2 <<EOF
kit: VENDORED COPY HAS DRIFTED FROM ITS PIN
  pinned  $PINNED
  actual  $ACTUAL

The kit is a frozen surface: edit it upstream at
  $SRC
then re-sync here with \`make kit-sync\`. Editing kit/ in place makes this lab's
copy silently different from every other lab's, which is the whole failure this
pin exists to prevent.
EOF
  exit 1
fi
echo "kit ok ($(awk '/^commit/ {print substr($2,1,8)}' "$KIT/PIN"))"
