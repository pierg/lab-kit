#!/usr/bin/env bash
# Vendor lab-kit into a lab, and scaffold anything the lab is missing.
#
#   bash install.sh /path/to/lab [--name "Lab name"] [--port 5181] [--content-kit /path]
#
# Two layers land in <lab>/kit/, in order:
#   1. content-kit — the shell, genres, craft, the present/address skills, verify.sh, kit_hash
#      (found beside this checkout as ../content-kit, or CONTENT_KIT=… / --content-kit)
#   2. the lab layer — DISCIPLINE, LADDER, MIGRATION, the ladder lint, the agents, the
#      mission / experiment / review skills, templates/ (the skills cite them), assets/paper
# Both are recorded in kit/PIN; `make kit-verify` hashes the whole tree. The engine (`ckit`)
# is not vendored — install it once with content-kit/install-engine.sh; the lab pins its version.
#
# Vendoring rather than referencing is deliberate: an agent session opened on a lab must find
# every rule inside that folder, with no sibling-repo path to resolve first.
set -euo pipefail

KIT_SRC="$(cd "$(dirname "$0")" && pwd)"
CONTENT_KIT="${CONTENT_KIT:-$(dirname "$KIT_SRC")/content-kit}"
LAB=""; NAME=""; PORT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --name) NAME="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --content-kit) CONTENT_KIT="$2"; shift 2 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) LAB="$1"; shift ;;
  esac
done

[ -n "$LAB" ] || { echo "usage: bash install.sh /path/to/lab [--name N] [--port P] [--content-kit DIR]" >&2; exit 2; }
[ -f "$CONTENT_KIT/install.sh" ] || {
  echo "lab-kit: content-kit not found at $CONTENT_KIT — clone it beside lab-kit, or pass --content-kit" >&2; exit 1; }
mkdir -p "$LAB"
LAB="$(cd "$LAB" && pwd)"
NAME="${NAME:-$(basename "$LAB")}"

scaffold() {  # scaffold <relative-target> <template-source>
  if [ -e "$LAB/$1" ]; then echo "  keep    $1"; else
    mkdir -p "$(dirname "$LAB/$1")"
    cp -r "$KIT_SRC/$2" "$LAB/$1"
    echo "  create  $1"
  fi
}

# The lab's own templates go first, so content-kit's installer finds them and keeps them.
echo "scaffolding lab layout"
scaffold README.md                   templates/README.lab.md
scaffold QUESTIONS.md                templates/QUESTIONS.md
scaffold lab.json                    templates/lab.json
scaffold Makefile                    templates/Makefile.lab
scaffold CLAUDE.md                   templates/CLAUDE.md
scaffold .gitignore                  templates/gitignore.lab
scaffold ops/STATE.md                templates/ops/STATE.md
scaffold ops/missions/TEMPLATE.md    templates/ops/missions/TEMPLATE.md
scaffold record/findings.md          templates/record/findings.md
scaffold record/claims.md            templates/record/claims.md
scaffold record/LESSONS.md           templates/record/LESSONS.md
scaffold record/RETIRED.md           templates/record/RETIRED.md
scaffold record/pins.json            templates/record/pins.json
scaffold record/logbook              templates/record/logbook
mkdir -p "$LAB"/experiments

# 1. content-kit: shell, genres, craft, present/address, verify.sh, kit_hash, the engine pin.
bash "$CONTENT_KIT/install.sh" "$LAB" --name "$NAME" ${PORT:+--port "$PORT"}

# 2. the lab layer, beside it.
echo "vendoring lab-kit -> $LAB/kit"
KIT="$LAB/kit"
mkdir -p "$KIT/tools" "$KIT/agents" "$KIT/skills"
for f in DISCIPLINE.md LADDER.md MIGRATION.md; do cp "$KIT_SRC/$f" "$KIT/$f"; done
for d in templates assets; do rm -rf "$KIT/$d"; cp -r "$KIT_SRC/$d" "$KIT/$d"; done   # the skills cite kit/templates/…
cp "$KIT_SRC/tools/ladder_lint.py" "$KIT/tools/ladder_lint.py"
cp "$KIT_SRC/tools/chronicle_lab.py" "$KIT/tools/chronicle_lab.py"
cp "$KIT_SRC/tools/layer_findings.py" "$KIT/tools/layer_findings.py"
cp "$KIT_SRC"/agents/*.md "$KIT/agents/"
for s in mission experiment review; do
  rm -rf "$KIT/skills/$s"
  cp -r "$KIT_SRC/skills/$s" "$KIT/skills/$s"
done
find "$KIT" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true

# Skills and agents are symlinked, so a kit re-sync updates them and drift is visible.
# `ln -sfn` onto an existing DIRECTORY silently creates the link *inside* it; a pre-existing
# real directory is the lab's own skill: leave it, say so, let the operator decide.
echo "linking skills + agents into .claude/"
mkdir -p "$LAB/.claude/skills" "$LAB/.claude/agents"
link_or_report() {  # link_or_report <target-in-.claude> <kit-relative-source>
  local dest="$1" src="$2"
  if [ -e "$dest" ] && [ ! -L "$dest" ]; then
    echo "  keep    ${dest#"$LAB/"}  (lab's own — kit's copy NOT linked)"
  else
    ln -sfn "$src" "$dest"
  fi
}
for s in mission experiment review; do
  link_or_report "$LAB/.claude/skills/$s" "../../kit/skills/$s"
done
for f in "$KIT"/agents/*.md; do
  b="$(basename "$f")"
  link_or_report "$LAB/.claude/agents/$b" "../../kit/agents/$b"
done

# The chronicle: the lab declares its record and its extractor once; a lab that has chosen
# otherwise keeps its choice (only absent keys are set).
python3 - "$LAB" <<'PY'
import json, sys
from pathlib import Path
lab = Path(sys.argv[1]); p = lab / "lab.json"; cfg = json.loads(p.read_text())
changed = False
if "record" not in cfg:
    # The sidebar: the ledger and standing surfaces a reader browses. Files only.
    cfg["record"] = [x for x in (
        "HISTORY.md", "QUESTIONS.md", "ARCHIVE.md",
        "ops/STATE.md",
        "record/findings.md", "record/claims.md", "record/LESSONS.md", "record/RETIRED.md",
        "record/logbook/lab.md",
    ) if (lab / x).exists()]
    changed = True
if "chronicle" not in cfg:
    # The scanner sweep: everything append-only the chronicle can extract dated headings from.
    sources = [x for x in ("HISTORY.md", "QUESTIONS.md", "ARCHIVE.md",
                           "ops/", "record/") if (lab / x).exists()]
    sources.append("experiments/*/PROBE.md")
    cfg["chronicle"] = {"sources": sources, "extractors": ["kit/tools/chronicle_lab.py"]}
    changed = True
if changed:
    p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    print("  set     lab.json record + chronicle (the timeline over the record)")
PY

# The lab declared its record above; regenerate the indices so the fresh gate is green.
command -v ckit >/dev/null 2>&1 && (cd "$LAB" && ckit lint --no-nav >/dev/null 2>&1 || true; ckit nav >/dev/null 2>&1 && echo "  set     content/chronicle.json (the record's timeline)")


# Pin: lab-kit's source line after content-kit's; one hash over the whole tree. kit/PIN is
# deliberately not ignored — it is the record of which kits this lab runs, and belongs in git.
SRC_SHA="$(git -C "$KIT_SRC" rev-parse HEAD 2>/dev/null || echo unknown)"
{
  grep -E '^source ' "$KIT/PIN" | grep -v '^source lab-kit '
  echo "source lab-kit $KIT_SRC $SRC_SHA"
} > "$KIT/PIN.tmp"
mv "$KIT/PIN.tmp" "$KIT/PIN"
bash "$KIT/verify.sh" --repin >/dev/null
echo "pinned  lab-kit@${SRC_SHA:0:8}"

echo
echo "done. next:"
echo "  cd $LAB && make check     # the gate (content gate + ladder lint, warn mode)"
echo "  cd $LAB && make docs      # read the pages on this lab's own port"
