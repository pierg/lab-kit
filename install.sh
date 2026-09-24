#!/usr/bin/env bash
# Vendor lab-kit into a lab, and scaffold anything the lab is missing.
#
#   bash install.sh /path/to/lab [--name "Lab name"] [--port 5181] [--content-kit /path/to/checkout]
#
# Needs only content-kit's engine, `ckit` ≥ 0.4, found in this order: --content-kit (a checkout;
# its bin/ckit), $CONTENT_KIT (the same), the `ckit` on PATH (an installed release), then a
# sibling checkout ../content-kit. No sibling is required.
#
# What lands, in order:
#   1. the lab layer: DISCIPLINE · LADDER · MIGRATION, the ladder lint and the other tools under
#      kit/tools/, the agents, the mission / experiment / review skills, templates/ and assets/
#      (the skills cite them), and kit/lab/ — the story genre and the lab's front door
#      (kit/lab/genres/), the dashboard page and the lab's stylesheet (kit/lab/shell/)
#   2. content-kit beside it, through `ckit init`: shell/ genres/ craft/ skills/{present,address},
#      verify.sh, kit_hash — pinned in kit/PIN, with the engine version in kit.json
#   3. the registration, in kit.json, through content-kit's extension points: genres, checks,
#      theme, refs (F-<n> and C-<n> become links), the chronicle extractor, and — for a lab with
#      "dashboard": true — the ladder generator, the dashboard shell page and its sidebar link
#
# Idempotent: re-running re-vendors, re-registers without duplicating, re-pins, and scaffolds only
# what is missing. Vendoring rather than referencing is deliberate: an agent session opened on a
# lab must find every rule inside that folder, with no sibling repo to resolve first.
set -euo pipefail

KIT_SRC="$(cd "$(dirname "$0")" && pwd)"
LAB=""; NAME=""; PORT=""; CK="${CONTENT_KIT:-}"
while [ $# -gt 0 ]; do
  case "$1" in
    --name) NAME="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --content-kit) CK="$2"; shift 2 ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    *) LAB="$1"; shift ;;
  esac
done
[ -n "$LAB" ] || { echo "usage: bash install.sh /path/to/lab [--name N] [--port P] [--content-kit DIR]" >&2; exit 2; }

# content-kit's engine
if [ -n "$CK" ]; then
  [ -x "$CK/bin/ckit" ] || { echo "lab-kit: no content-kit checkout at $CK (expected $CK/bin/ckit)" >&2; exit 1; }
  CKIT="$CK/bin/ckit"
elif command -v ckit >/dev/null 2>&1; then
  CKIT="ckit"
elif [ -x "$(dirname "$KIT_SRC")/content-kit/bin/ckit" ]; then
  CKIT="$(dirname "$KIT_SRC")/content-kit/bin/ckit"
else
  echo "lab-kit: content-kit's engine not found — uv tool install git+https://github.com/pierg/content-kit@v0.4.0, or pass --content-kit" >&2
  exit 1
fi
CKIT_VERSION="$("$CKIT" version)"
python3 - "$CKIT_VERSION" <<'PY' || { echo "lab-kit 0.2 needs content-kit ≥ 0.4 (its extension points); found ckit $CKIT_VERSION" >&2; exit 1; }
import sys
major, minor = (int(x) for x in sys.argv[1].split(".")[:2])
sys.exit(0 if (major, minor) >= (0, 4) else 1)
PY

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

# The lab's own templates go first, so content-kit's init finds them and keeps them. Only a
# fresh lab is scaffolded: an existing lab's record, ops and experiments are its own, and a kit
# upgrade never adds a file to them.
if [ -f "$LAB/kit.json" ] || [ -f "$LAB/lab.json" ]; then
  echo "existing lab: its layout is left exactly as it is"
  [ -f "$LAB/lab.json" ] && [ ! -f "$LAB/kit.json" ] && echo "  keep    lab.json  (deprecated — git mv lab.json kit.json when convenient)"
  FRESH=""
else
  echo "scaffolding lab layout"
  FRESH=1
fi
[ -n "$FRESH" ] && {
scaffold kit.json                    templates/kit.json
scaffold README.md                   templates/README.lab.md
scaffold QUESTIONS.md                templates/QUESTIONS.md
scaffold Makefile                    templates/Makefile.lab
scaffold AGENTS.md                   templates/AGENTS.md
if [ ! -e "$LAB/CLAUDE.md" ] && [ ! -L "$LAB/CLAUDE.md" ]; then
  printf '@AGENTS.md\n' > "$LAB/CLAUDE.md"
  echo "  create  CLAUDE.md"
fi
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
}

# 1. the lab layer. It goes in before content-kit's init, because a lab's kit.json may already
# name these files (a re-sync, or the example lab) and init regenerates the indices at its end.
# init never touches them: it owns only kit/shell, kit/genres, kit/craft, its two skills,
# kit/tools/kit_hash.py and kit/verify.sh.
echo "vendoring lab-kit -> $LAB/kit"
KIT="$LAB/kit"
mkdir -p "$KIT/tools" "$KIT/agents" "$KIT/skills"
for f in DISCIPLINE.md LADDER.md MIGRATION.md; do cp "$KIT_SRC/$f" "$KIT/$f"; done
for d in templates assets; do rm -rf "${KIT:?}/$d"; cp -r "$KIT_SRC/$d" "$KIT/$d"; done   # the skills cite kit/templates/…
for t in ladder_lint chronicle_lab layer_findings checks_lab ladder; do cp "$KIT_SRC/tools/$t.py" "$KIT/tools/$t.py"; done
cp "$KIT_SRC"/agents/*.md "$KIT/agents/"
for s in mission experiment review; do
  rm -rf "${KIT:?}/skills/$s"
  cp -r "$KIT_SRC/skills/$s" "$KIT/skills/$s"
done
rm -rf "${KIT:?}/lab"
mkdir -p "$KIT/lab"
cp -r "$KIT_SRC/genres" "$KIT/lab/genres"
cp -r "$KIT_SRC/shell" "$KIT/lab/shell"
find "$KIT" \( -name __pycache__ -o -name .DS_Store \) -prune -exec rm -rf {} + 2>/dev/null || true

# 2. content-kit: the shell, genres, craft, present/address, verify.sh, kit_hash, the engine pin.
"$CKIT" init "$LAB" --name "$NAME" ${PORT:+--port "$PORT"}

# One body per kit skill, linked from .agents/skills. .claude/skills is a single relative
# symlink to that directory. A real directory already using a kit skill's name is replaced.
# A real directory left under .claude/skills whose name is not a kit skill stays: it belongs
# to the lab and moves to .agents/skills. Agents stay per-name links under .claude/agents.
echo "linking skills + agents"
mkdir -p "$LAB/.agents/skills" "$LAB/.claude/agents"
link_skill() {  # link_skill <skill-name> <absolute-body>
  local skill="$1" body="$2"
  local dest="$LAB/.agents/skills/$skill" rel
  rel="$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$body" "$LAB/.agents/skills")"
  if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$rel" ]; then
    return
  fi
  if [ -d "$dest" ] && [ ! -L "$dest" ]; then
    echo "  replace .agents/skills/$skill  (it shadowed the kit skill)"
    rm -rf "$dest"
  elif [ -L "$dest" ] || [ -f "$dest" ]; then
    rm -f "$dest"
  fi
  ln -s "$rel" "$dest"
  echo "  link    .agents/skills/$skill"
}
while IFS= read -r body; do
  [ -n "$body" ] || continue
  link_skill "$(basename "$body")" "$body"
done < <(find "$KIT/skills" "$KIT"/*/skills -mindepth 1 -maxdepth 1 -type d -exec test -f '{}/SKILL.md' \; -print 2>/dev/null | sort -u)
claude_skills="$LAB/.claude/skills"
if [ -L "$claude_skills" ]; then
  [ "$(readlink "$claude_skills")" = "../.agents/skills" ] || ln -sfn "../.agents/skills" "$claude_skills"
elif [ -d "$claude_skills" ]; then
  find "$claude_skills" -mindepth 1 -maxdepth 1 \( -type l -o -type f \) -exec rm -f {} +
  if [ -n "$(find "$claude_skills" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
    find "$claude_skills" -mindepth 1 -maxdepth 1 -type d -print | while read -r kept; do
      echo "  keep    .claude/skills/$(basename "$kept")  (lab's own — move it to .agents/skills/$(basename "$kept"))"
    done
  else
    rmdir "$claude_skills"
    ln -s "../.agents/skills" "$claude_skills"
    echo "  link    .claude/skills"
  fi
else
  mkdir -p "$LAB/.claude"
  ln -s "../.agents/skills" "$claude_skills"
  echo "  link    .claude/skills"
fi
for f in "$KIT"/agents/*.md; do
  b="$(basename "$f")"
  dest="$LAB/.claude/agents/$b"
  if [ -e "$dest" ] && [ ! -L "$dest" ]; then
    echo "  keep    .claude/agents/$b  (lab's own)"
  else
    ln -sfn "../../kit/agents/$b" "$dest"
  fi
done

# 3. Register the lab layer through content-kit's extension points. Only lab-kit's own entries are
# added; whatever the lab declared itself is kept, after them where order matters.
python3 - "$LAB" <<'PY'
import json, sys
from pathlib import Path
lab = Path(sys.argv[1])
p = lab / "kit.json" if (lab / "kit.json").is_file() or not (lab / "lab.json").is_file() else lab / "lab.json"
cfg = json.loads(p.read_text())
said = []

def add(key, item, first=False):
    cur = cfg.get(key)
    items = [] if cur in (None, "", {}) else (list(cur) if isinstance(cur, list) else [cur])
    if item in items:
        return
    items = [item] + items if first else items + [item]
    cfg[key] = items
    said.append(key)

if "record" not in cfg:
    # The sidebar: the ledger and standing surfaces a reader browses. Files only.
    cfg["record"] = [x for x in (
        "HISTORY.md", "QUESTIONS.md", "ARCHIVE.md",
        "ops/STATE.md",
        "record/findings.md", "record/claims.md", "record/LESSONS.md", "record/RETIRED.md",
        "record/logbook/lab.md",
    ) if (lab / x).exists()]
    said.append("record")
elif (lab / "record/LESSONS.md").exists() and "record/LESSONS.md" not in cfg["record"]:
    print('  note    record/LESSONS.md exists but kit.json "record" does not list it — '
          "the viewer and the chronicle will not see it until it is added")
if "chronicle" not in cfg:
    # The scanner sweep: everything append-only the chronicle can extract dated headings from.
    sources = [x for x in ("HISTORY.md", "QUESTIONS.md", "ARCHIVE.md", "ops/", "record/") if (lab / x).exists()]
    sources.append("experiments/*/PROBE.md")
    cfg["chronicle"] = {"sources": sources, "extractors": ["kit/tools/chronicle_lab.py"]}
    said.append("chronicle")
else:
    ex = cfg["chronicle"].setdefault("extractors", [])
    if "kit/tools/chronicle_lab.py" not in ex:
        ex.append("kit/tools/chronicle_lab.py")
        said.append("chronicle.extractors")

add("genres", "kit/lab/genres/genres_lab.json", first=True)   # the lab's own overrides stay after it
add("checks", "kit/tools/checks_lab.py")
add("theme", "kit/lab/shell/lab.css", first=True)              # the lab's own theme stays after it
findings = cfg.get("findings", "record/findings.md")
claims = cfg.get("claims", "record/claims.md")
add("refs", {"pattern": r"F-\d+(?:\.\d+)?", "href": f"/shell/record.html?p={findings}#{{id}}"})
add("refs", {"pattern": r"C-\d+", "href": f"/shell/record.html?p={claims}#{{id}}"})
if cfg.get("dashboard") is True or cfg.get("home") in ("dashboard", "dashboard.html"):
    add("generators", "kit/tools/ladder.py")
    pages = cfg.get("shell_pages") or {}
    if pages.get("dashboard.html") != "kit/lab/shell/dashboard.html":
        pages["dashboard.html"] = "kit/lab/shell/dashboard.html"
        cfg["shell_pages"] = pages
        said.append("shell_pages")
    add("links", {"label": "Dashboard", "href": "/shell/dashboard.html", "title": "The record as a status board"}, first=True)
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
if said:
    print(f"  set     {p.name}: " + ", ".join(dict.fromkeys(said)))
PY

# Pin: lab-kit's source line after content-kit's; one hash over the whole tree. kit/PIN is
# deliberately not ignored — it is the record of which kits this lab runs, and belongs in git.
SRC_SHA="$(git -C "$KIT_SRC" rev-parse --verify -q HEAD 2>/dev/null || true)"
SRC_SHA="${SRC_SHA:-unknown}"
SRC_WHERE="$(python3 - "$KIT_SRC" <<'PY'
import re, subprocess, sys
src = sys.argv[1]
try:
    r = subprocess.run(["git", "-C", src, "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
except OSError:
    r = ""
m = re.match(r"^(?:ssh://)?git@([^:/]+)[:/](.+?)(?:\.git)?/?$", r)
if m:
    r = f"https://{m.group(1)}/{m.group(2)}"
r = re.sub(r"\.git/?$", "", re.sub(r"^(https?://)[^@/]+@", r"\1", r)).rstrip("/")
print(r or src)
PY
)"
{
  grep -E '^source ' "$KIT/PIN" | grep -v '^source lab-kit '
  echo "source lab-kit $SRC_WHERE $SRC_SHA"
} > "$KIT/PIN.tmp"
mv "$KIT/PIN.tmp" "$KIT/PIN"
bash "$KIT/verify.sh" --repin >/dev/null
echo "pinned  lab-kit@${SRC_SHA:0:8}"

# The registration changed what the indices cover; regenerate so the fresh gate is green.
(cd "$LAB" && "$CKIT" nav >/dev/null) && echo "  set     content/ indices regenerated (ckit nav)"

echo
echo "done. next:"
echo "  cd $LAB && make check     # the gate (content gate + ladder lint)"
echo "  cd $LAB && make docs      # read the pages on this lab's own port"
