#!/usr/bin/env bash
# End-to-end: install the kit into a scratch lab, run its gate, serve it, read a page.
# This is the check that catches path-resolution breakage, which unit tests cannot see
# because the whole point of the kit is that it runs from a directory it was copied into —
# with the content-kit engine found on PATH, never inside the lab.
set -euo pipefail
KIT="$(cd "$(dirname "$0")/.." && pwd)"
CONTENT_KIT="${CONTENT_KIT:-$(dirname "$KIT")/content-kit}"
[ -d "$CONTENT_KIT" ] || { echo "e2e: content-kit not found at $CONTENT_KIT" >&2; exit 1; }
export CONTENT_KIT PATH="$CONTENT_KIT/bin:$PATH"
TMP="$(mktemp -d)"
trap 'cd /; [ -f "$TMP/lab/.serve.pid" ] && kill "$(cat "$TMP/lab/.serve.pid")" 2>/dev/null; rm -rf "$TMP"' EXIT

LAB="$TMP/lab"
echo "--- install ---"
bash "$KIT/install.sh" "$LAB" --name "Scratch Lab" --port 5399 >/dev/null

for f in lab.json Makefile CLAUDE.md README.md QUESTIONS.md ops/STATE.md record/findings.md record/claims.md \
         kit/PIN kit/DISCIPLINE.md kit/LADDER.md kit/tools/ladder_lint.py kit/verify.sh kit/tools/kit_hash.py \
         kit/shell/lib.css kit/genres/GENRES.md kit/craft/CRAFT.md kit/skills/present/SKILL.md kit/skills/address/SKILL.md; do
  [ -e "$LAB/$f" ] || { echo "e2e: install did not create $f" >&2; exit 1; }
done
[ -L "$LAB/.claude/skills/mission" ] || { echo "e2e: lab skills not symlinked" >&2; exit 1; }
[ -L "$LAB/.claude/skills/present" ] || { echo "e2e: content skills not symlinked" >&2; exit 1; }
[ -L "$LAB/.claude/agents/reviewer.md" ] || { echo "e2e: agents not symlinked" >&2; exit 1; }
grep -q '^source content-kit ' "$LAB/kit/PIN" && grep -q '^source lab-kit ' "$LAB/kit/PIN" \
  || { echo "e2e: PIN does not record both kits" >&2; exit 1; }
grep -q '"ckit": "'"$(ckit version)"'"' "$LAB/lab.json" || { echo "e2e: lab.json lacks the engine pin" >&2; exit 1; }
grep -q '"ladder": "warn"' "$LAB/lab.json" || { echo "e2e: lab.json lost its ladder mode" >&2; exit 1; }
( cd "$LAB" && git init -q && git add -A && git status --porcelain kit/PIN | grep -q . ) \
  || { echo "e2e: kit/PIN is not stageable — it must be tracked, not ignored" >&2; exit 1; }
rm -rf "$LAB/.git"
echo "install ok"

echo "--- gate on a fresh lab ---"
( cd "$LAB" && make check >/dev/null ) || { echo "e2e: make check failed on a fresh lab" >&2; exit 1; }
( cd "$LAB" && ckit new concept probe-term >/dev/null && make check >/dev/null ) \
  || { echo "e2e: make check failed after scaffolding a concept" >&2; exit 1; }
echo "gate ok"

echo "--- kit drift is detected ---"
echo "# tampered" >> "$LAB/kit/DISCIPLINE.md"
if ( cd "$LAB" && make kit-verify >/dev/null 2>&1 ); then
  echo "e2e: tampering with the vendored kit was NOT detected" >&2; exit 1
fi
echo "drift detection ok"
( cd "$LAB" && make kit-sync >/dev/null && make kit-verify >/dev/null )
echo "re-sync ok"

echo "--- ladder lint sees a real violation ---"
cat >> "$LAB/record/claims.md" <<'EOM'

## C-2 · Asserted from nowhere
Nothing licenses this.
EOM
printf '# Note — LIVE\n\nSee F-404.\n' > "$LAB/content/notes/probe.md"
OUT="$( cd "$LAB" && python3 kit/tools/ladder_lint.py 2>&1 )"
echo "$OUT" | grep -q "F-404" || { echo "e2e: unknown finding id not reported" >&2; exit 1; }
echo "$OUT" | grep -q "C-2" || { echo "e2e: unlicensed claim not reported" >&2; exit 1; }
( cd "$LAB" && python3 kit/tools/ladder_lint.py --strict >/dev/null 2>&1 ) && \
  { echo "e2e: --strict did not fail on hard problems" >&2; exit 1; }
echo "ladder lint ok"

echo "--- library mode ---"
python3 - "$LAB/lab.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]); c = json.loads(p.read_text()); c["ladder"] = "off"
p.write_text(json.dumps(c, indent=2) + "\n")
PY
OUT="$( cd "$LAB" && python3 kit/tools/ladder_lint.py 2>&1 )"
echo "$OUT" | grep -q "library mode" || { echo "e2e: ladder=off did not enter library mode" >&2; exit 1; }
echo "$OUT" | grep -q "F-404" && { echo "e2e: library mode still ran the checks" >&2; exit 1; }
python3 - "$LAB/lab.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]); c = json.loads(p.read_text()); c["ladder"] = "warn"
p.write_text(json.dumps(c, indent=2) + "\n")
PY
echo "library mode ok"

echo "--- serve ---"
( cd "$LAB" && make docs >/dev/null )
sleep 0.7
curl -fsS "http://127.0.0.1:5399/" | grep -q "Scratch Lab" || { echo "e2e: landing page did not render" >&2; exit 1; }
curl -fsS "http://127.0.0.1:5399/shell/lib.css" >/dev/null || { echo "e2e: /shell/ mount not served" >&2; exit 1; }
curl -fsS "http://127.0.0.1:5399/content/concepts/probe-term/" | grep -q "defn" || { echo "e2e: concept page not served" >&2; exit 1; }
( cd "$LAB" && make down >/dev/null )
echo "serve ok"

echo "e2e ok"
