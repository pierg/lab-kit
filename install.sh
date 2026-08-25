#!/usr/bin/env bash
# Vendor this kit into a lab, and scaffold anything the lab is missing.
#
#   bash install.sh /path/to/lab [--name "Lab name"] [--port 5181]
#
# Vendoring rather than referencing is deliberate: an agent session opened on a lab
# must find every capability and every rule inside that folder, with no sibling-repo
# path to resolve first. The PIN file plus `make kit-verify` is what keeps four
# vendored copies from quietly becoming four different kits.
set -euo pipefail

KIT_SRC="$(cd "$(dirname "$0")" && pwd)"
LAB=""; NAME=""; PORT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --name) NAME="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) LAB="$1"; shift ;;
  esac
done

[ -n "$LAB" ] || { echo "usage: bash install.sh /path/to/lab [--name N] [--port P]" >&2; exit 2; }
mkdir -p "$LAB"
LAB="$(cd "$LAB" && pwd)"
NAME="${NAME:-$(basename "$LAB")}"

echo "vendoring kit -> $LAB/kit"
rm -rf "$LAB/kit"
mkdir -p "$LAB/kit"
tar -C "$KIT_SRC" \
    --exclude='.git' --exclude='__pycache__' --exclude='PIN' \
    --exclude='.serve.pid' --exclude='.serve.log' \
    -cf - . | tar -C "$LAB/kit" -xf -

# Pin: the kit's own commit plus a content hash of exactly what landed.
SRC_SHA="$(git -C "$KIT_SRC" rev-parse HEAD 2>/dev/null || echo unknown)"
HASH="$(python3 "$LAB/kit/tools/kit_hash.py" "$LAB/kit")"
cat > "$LAB/kit/PIN" <<EOF
source  $KIT_SRC
commit  $SRC_SHA
hash    $HASH
EOF
echo "pinned  commit=$SRC_SHA"

scaffold() {  # scaffold <relative-target> <template-source>
  if [ -e "$LAB/$1" ]; then echo "  keep    $1"; else
    mkdir -p "$(dirname "$LAB/$1")"
    cp -r "$KIT_SRC/$2" "$LAB/$1"
    echo "  create  $1"
  fi
}

echo "scaffolding lab layout"
scaffold lab.json                    templates/lab.json
scaffold Makefile                    templates/Makefile.lab
scaffold CLAUDE.md                   templates/CLAUDE.md
scaffold ops/STATE.md                templates/ops/STATE.md
scaffold ops/missions/TEMPLATE.md    templates/ops/missions/TEMPLATE.md
scaffold record/findings.md          templates/record/findings.md
scaffold record/claims.md            templates/record/claims.md
scaffold record/RETIRED.md           templates/record/RETIRED.md
scaffold record/pins.json            templates/record/pins.json
scaffold record/logbook              templates/record/logbook
mkdir -p "$LAB"/content/{entries,concepts,notes,hubs,projects,papers} "$LAB"/experiments
touch "$LAB"/content/entries/.gitkeep "$LAB"/content/concepts/.gitkeep

# lab.json gets the real name/port on first creation only.
python3 - "$LAB" "$NAME" "${PORT:-}" <<'PY'
import json, sys
from pathlib import Path
lab, name, port = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
p = lab / "lab.json"
cfg = json.loads(p.read_text())
if cfg.get("name", "").startswith("<"):
    cfg["name"] = name
    if port:
        cfg["port"] = int(port)
    p.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"  set     lab.json name={name}" + (f" port={port}" if port else ""))
PY

# Skills and agents are symlinked, so a kit re-sync updates them and drift is visible.
echo "linking skills + agents into .claude/"
mkdir -p "$LAB/.claude/skills" "$LAB/.claude/agents"
for d in "$LAB"/kit/skills/*/; do
  ln -sfn "../../kit/skills/$(basename "$d")" "$LAB/.claude/skills/$(basename "$d")"
done
for f in "$LAB"/kit/agents/*.md; do
  ln -sfn "../../kit/agents/$(basename "$f")" "$LAB/.claude/agents/$(basename "$f")"
done

# The lab needs its own ignores; kit/PIN is deliberately NOT among them — the pin
# is the record of which kit this lab is running, and it belongs in git.
if [ ! -e "$LAB/.gitignore" ]; then
  cp "$KIT_SRC/templates/gitignore.lab" "$LAB/.gitignore"
  echo "  create  .gitignore"
fi

echo
echo "done. next:"
echo "  cd $LAB && make check     # the gate (ladder lint starts in warn mode)"
echo "  cd $LAB && make serve     # read the pages on this lab's own port"
