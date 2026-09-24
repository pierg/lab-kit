#!/usr/bin/env bash
# End-to-end: install lab-kit (with content-kit's engine, found the way install.sh finds it) into
# a copy of the example lab and into an empty directory; run their gates; prove every extension
# point lab-kit registers reaches the reader (story, record checks, dashboard, chronicle kinds and
# cards, id links, theme); plant a violation for each check and watch it fire by name; serve;
# export; and prove drift, re-sync and library mode. This is the check unit tests cannot give: the
# kit runs from a directory it was copied into, with only `ckit` on PATH.
set -euo pipefail
KIT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -n "${CONTENT_KIT:-}" ]; then
  export PATH="$(cd "$CONTENT_KIT" && pwd)/bin:$PATH"
elif ! command -v ckit >/dev/null 2>&1 && [ -x "$(dirname "$KIT")/content-kit/bin/ckit" ]; then
  export PATH="$(dirname "$KIT")/content-kit/bin:$PATH"
fi
command -v ckit >/dev/null 2>&1 || { echo "e2e: no content-kit engine (ckit) — install it or set CONTENT_KIT" >&2; exit 1; }
unset CONTENT_KIT   # from here on the kit must find the engine on PATH, like any user's lab
TMP="$(mktemp -d)"
PORT=5399
SPORT=5398
trap 'cd /; for l in "$TMP/lab" "$TMP/fresh"; do [ -f "$l/.serve.pid" ] && kill "$(cat "$l/.serve.pid")" 2>/dev/null; done; [ -n "${HTTPD:-}" ] && kill "$HTTPD" 2>/dev/null; rm -rf "$TMP"' EXIT
fail() { echo "e2e: $*" >&2; exit 1; }
json_set() {  # json_set <file> <python statements over c>
  python3 - "$1" "$2" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]); c = json.loads(p.read_text()); exec(sys.argv[2]); p.write_text(json.dumps(c, indent=2) + "\n")
PY
}

echo "--- a fresh lab: install into an empty directory, and it opens green ---"
FRESH="$TMP/fresh"
bash "$KIT/install.sh" "$FRESH" --name "Scratch Lab" --port $PORT >/dev/null
for f in kit.json Makefile AGENTS.md CLAUDE.md README.md QUESTIONS.md ops/STATE.md record/findings.md record/claims.md \
         record/LESSONS.md kit/PIN kit/DISCIPLINE.md kit/LADDER.md kit/verify.sh kit/tools/kit_hash.py \
         kit/shell/lib.css kit/genres/GENRES.md kit/craft/CRAFT.md kit/skills/present/SKILL.md kit/skills/address/SKILL.md \
         kit/templates/experiments/PROBE.md kit/assets/paper/preamble.tex \
         kit/tools/ladder_lint.py kit/tools/chronicle_lab.py kit/tools/layer_findings.py kit/tools/checks_lab.py kit/tools/ladder.py \
         kit/lab/genres/genres_lab.json kit/lab/genres/GENRES.md kit/lab/genres/skeletons/story/index.html \
         kit/lab/shell/dashboard.html kit/lab/shell/lab.css; do
  [ -e "$FRESH/$f" ] || fail "install did not create $f"
done
[ -e "$FRESH/lab.json" ] && fail "a fresh lab must get kit.json, not lab.json"
[ -L "$FRESH/.claude/skills" ] && [ "$(readlink "$FRESH/.claude/skills")" = "../.agents/skills" ] \
  || fail ".claude/skills must be one relative symlink to ../.agents/skills"
[ -L "$FRESH/.agents/skills/mission" ] || fail "lab skills not symlinked"
[ -L "$FRESH/.agents/skills/present" ] || fail "content skills not symlinked"
[ "$(cat "$FRESH/CLAUDE.md")" = "@AGENTS.md" ] || fail "CLAUDE.md must be exactly @AGENTS.md"
[ -f "$FRESH/AGENTS.md" ] && [ ! -L "$FRESH/AGENTS.md" ] || fail "AGENTS.md must be a regular file"
[ -L "$FRESH/.claude/agents/reviewer.md" ] || fail "agents not symlinked"
grep -q '^source content-kit ' "$FRESH/kit/PIN" && grep -q '^source lab-kit ' "$FRESH/kit/PIN" || fail "PIN does not record both kits"
[ "$(awk '/^source /{print NF}' "$FRESH/kit/PIN" | sort -u)" = 4 ] || fail "PIN source lines must keep four fields"
grep -q "\"ckit\": \"$(ckit version)\"" "$FRESH/kit.json" || fail "kit.json lacks the engine pin"
grep -q '"ladder": "warn"' "$FRESH/kit.json" || fail "kit.json lost its ladder mode"
python3 - "$FRESH/kit.json" <<'PY' || fail "install did not register lab-kit through the extension points"
import json, sys
c = json.load(open(sys.argv[1]))
assert c["genres"][0] == "kit/lab/genres/genres_lab.json", c["genres"]
assert "kit/tools/checks_lab.py" in c["checks"], c["checks"]
assert "kit/lab/shell/lab.css" in c["theme"], c["theme"]
assert {r["pattern"] for r in c["refs"]} == {r"F-\d+(?:\.\d+)?", r"C-\d+"}, c["refs"]
assert "kit/tools/chronicle_lab.py" in c["chronicle"]["extractors"] and c["chronicle"].get("sources"), c["chronicle"]
assert c.get("dashboard") is True and c["shell_pages"]["dashboard.html"] == "kit/lab/shell/dashboard.html", c
assert "kit/tools/ladder.py" in c["generators"] and c["links"][0]["label"] == "Dashboard", c
PY
bash "$KIT/install.sh" "$FRESH" >/dev/null
python3 - "$FRESH/kit.json" <<'PY' || fail "re-running install.sh duplicated a registration"
import json, sys
c = json.load(open(sys.argv[1]))
for k in ("genres", "checks", "theme", "refs", "generators", "links"):
    assert len(c[k]) == len({json.dumps(x, sort_keys=True) for x in c[k]}), (k, c[k])
PY
( cd "$FRESH" && git init -q && git add -A && git status --porcelain kit/PIN | grep -q . ) \
  || fail "kit/PIN is not stageable — it must be tracked, not ignored"
rm -rf "$FRESH/.git"
( cd "$FRESH" && python3 kit/tools/ladder_lint.py | grep -q ": 0 error(s)" ) \
  || { ( cd "$FRESH" && python3 kit/tools/ladder_lint.py >&2 ); fail "a freshly scaffolded lab does not report 0 errors"; }
for t in ladder_lint chronicle_lab layer_findings checks_lab; do
  ( cd "$FRESH" && python3 "kit/tools/$t.py" --selftest >/dev/null ) || fail "$t selftest failed from the vendored copy"
done
( cd "$FRESH" && make check >/dev/null ) || fail "make check failed on a fresh lab"
( cd "$FRESH" && ckit genres | grep -q '^story ' ) || fail "ckit genres does not list the lab's story genre"
( cd "$FRESH" && ckit new story first-result >/dev/null ) || fail "ckit new story failed"
OUT="$(cd "$FRESH" && ckit lint 2>&1 || true)"
echo "$OUT" | grep -q "stories/first-result/index.html: the opening line names no finding" \
  && fail "the story skeleton's placeholder row must satisfy bound_ids until it is replaced"
echo "fresh lab ok"

echo "--- the example lab: installed, green in strict mode ---"
LAB="$TMP/lab"
rsync -a --exclude kit --exclude .claude --exclude 'content/*.json' "$KIT/example-lab/" "$LAB/"
rm "$LAB/record/LESSONS.md"   # an existing lab without a lessons ledger: a kit upgrade must not add one
bash "$KIT/install.sh" "$LAB" >/dev/null
[ -e "$LAB/record/LESSONS.md" ] && fail "install added a file to an existing lab's record"
cp "$KIT/example-lab/record/LESSONS.md" "$LAB/record/LESSONS.md"
json_set "$LAB/kit.json" "c['port'] = $PORT"   # the example keeps its own port; the test needs a free one
( cd "$LAB" && ckit lint >/dev/null && make check >/dev/null ) \
  || { ( cd "$LAB" && make check >&2 ); fail "the example lab is not green"; }
grep -q '"ladder": "strict"' "$LAB/kit.json" || fail "the example lab must run the ladder in strict mode"
python3 - "$LAB/content" <<'PY' || fail "the example lab's generated indices are wrong"
import json, sys
from pathlib import Path
c = Path(sys.argv[1])
cat = json.loads((c / "catalog.json").read_text())
keys = [g["key"] for g in cat["groups"]]
assert keys.index("stories") == keys.index("projects") + 1, keys           # the sidebar order of 0.3
assert [s["slug"] for s in cat["stories"]] == ["nearly-sorted", "small-arrays"], cat["stories"]
assert cat["links"][0]["href"] == "/shell/dashboard.html", cat.get("links")
chron = json.loads((c / "chronicle.json").read_text())
names = [k["name"] for k in chron["kinds"]]
assert names[-5:] == ["experiment", "finding", "claim", "mission", "entry"], names
assert chron["cards"]["view"] == "experiments" and len(chron["cards"]["items"]) == 2, chron.get("cards")
assert {"experiment", "finding", "mission", "pivot", "kill", "decision"} <= {e["kind"] for e in chron["events"]}
lad = json.loads((c / "ladder.json").read_text())
assert [f["id"] for f in lad["findings"]] == ["F-1", "F-2", "F-3"], lad["findings"]
assert [x["slug"] for x in lad["experiments"]] == ["20260905-e2-small-n", "20260901-e1-nearly-sorted"], lad["experiments"]
assert lad["claims"][0]["rests_on"] == ["F-1", "F-2"], lad["claims"]
assert lad["now"] and "Complete" in lad["now"]["summary"], lad["now"]
si = json.loads((c / "search-index.json").read_text())
assert {r["kind"] for r in si if "/stories/" in r["href"]} == {"story"}
PY
echo "example lab ok"

echo "--- every lab check fires by name on a planted page ---"
cp -R "$LAB/content/stories/nearly-sorted" "$LAB/content/stories/unbound"
python3 - "$LAB/content/stories/unbound/index.html" <<'PY'
import re, sys
from pathlib import Path
p = Path(sys.argv[1]); t = p.read_text()
t = re.sub(r'(<p class="sub">.*?)</p>', lambda m: re.sub(r"<code>F-\d+</code>", "the rows", m.group(1)) + "</p>", t, count=1, flags=re.S)
p.write_text(t)
PY
cp -R "$LAB/content/stories/nearly-sorted" "$LAB/content/stories/sectionless"
python3 - "$LAB/content/stories/sectionless/index.html" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1]); t = p.read_text()
p.write_text(t.replace('<h2 id="not">', '<h2 id="not-shown">'))
PY
mkdir -p "$LAB/content/concepts/cites-a-row"
sed 's/depends on the routine and the input.s order/depends on the routine and on F-1/' "$LAB/content/concepts/comparison-count/index.html" \
  > "$LAB/content/concepts/cites-a-row/index.html"
OUT="$(cd "$LAB" && ckit lint 2>&1 || true)"
echo "$OUT" | grep -q "stories/unbound/index.html: the opening line names no finding" || fail "bound_ids did not fire: $OUT"
echo "$OUT" | grep -q 'stories/sectionless/index.html: no <h2 id="not"> section' || fail "a story's fixed sections are not checked"
echo "$OUT" | grep -q "concepts/cites-a-row/index.html: cites F-1 inside its defn" || fail "defn_no_findings did not fire"
rm -rf "$LAB/content/stories/unbound" "$LAB/content/stories/sectionless" "$LAB/content/concepts/cites-a-row"
printf '# Note — LIVE\n\nSee F-404.\n' > "$LAB/content/notes/probe.md"
OUT="$(cd "$LAB" && python3 kit/tools/ladder_lint.py 2>&1 || true)"
echo "$OUT" | grep -q "F-404" || fail "the ladder lint missed an unknown finding id"
( cd "$LAB" && make check >/dev/null 2>&1 ) && fail "strict mode passed a page citing an unknown row"
rm "$LAB/content/notes/probe.md"
( cd "$LAB" && ckit lint >/dev/null && make check >/dev/null ) || fail "the example lab did not return to green"
echo "lab checks ok"

echo "--- the dashboard's data is an index: stale fails the gate ---"
python3 - "$LAB/content/ladder.json" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p)); d["findings"][0]["title"] = "tampered"; json.dump(d, open(p, "w"))
PY
OUT="$(cd "$LAB" && ckit check 2>&1 || true)"
echo "$OUT" | grep -q "content/ladder.json" || fail "a stale ladder.json passed the gate"
( cd "$LAB" && ckit lint >/dev/null && make check >/dev/null ) || fail "regenerating did not restore ladder.json"
echo "dashboard index ok"

echo "--- figures-check: an unprepared generator is a hard failure ---"
GEN="$LAB/assets/figures/generators"
mkdir -p "$GEN"
printf 'open("wrote.marker", "w").write("drawn")\n' > "$GEN/gen_fig_unprepared.py"
( cd "$LAB" && make figures-check >/dev/null 2>&1 ) && fail "figures-check passed a generator with no --check mode"
[ -e "$GEN/wrote.marker" ] && fail "the unprepared generator drew its figure before being refused"
rm -f "$GEN/gen_fig_unprepared.py"
printf 'import sys\nif "--check" in sys.argv:\n    sys.exit(1)\n' > "$GEN/gen_fig_failing.py"
( cd "$LAB" && make figures-check >/dev/null 2>&1 ) && fail "figures-check passed a generator whose --check exits 1"
rm -f "$GEN/gen_fig_failing.py"
printf 'import sys\nif "--check" in sys.argv:\n    sys.exit(0)\n' > "$GEN/gen_fig_passing.py"
( cd "$LAB" && make figures-check >/dev/null 2>&1 ) || fail "figures-check failed a generator whose --check exits 0"
rm -rf "$LAB/assets"
OUT="$( cd "$LAB" && make figures-check 2>&1 )" || fail "figures-check failed with no generators present"
echo "$OUT" | grep -q "nothing to check" || fail "figures-check did not print the no-op line"
echo "figures-check ok"

echo "--- serve: the story, the dashboard, the chronicle, the theme, the id links ---"
( cd "$LAB" && make docs >/dev/null )
sleep 0.8
B="http://127.0.0.1:$PORT"
curl -sI "$B/" | grep -q '^Location: /content/projects/sorting-crossover/' || fail "the lab's front door is not its home"
curl -fsS "$B/shell/dashboard.html" | grep -q "<title>Dashboard</title>" || fail "the dashboard shell page is not served"
curl -fsS "$B/shell/theme.css" | grep -q "hb-kind-story" || fail "lab-kit's stylesheet is not in the theme"
curl -fsS "$B/shell/chronicle.html" >/dev/null || fail "chronicle page not served"
curl -fsS "$B/content/chronicle.json" | grep -q '"view": "experiments"' || fail "chronicle.json lacks the Experiments cards"
curl -fsS "$B/content/stories/nearly-sorted/" | grep -q "<code>F-1</code>" || fail "a story is not served"
curl -fsS "$B/shell/record.html?p=record/findings.md" | grep -q "marked.umd.js" || fail "record viewer not served"
curl -fsS "$B/record/findings.md" | grep -q "## F-1" || fail "the ledger is not served raw to the viewer"
( cd "$LAB" && make down >/dev/null )
echo "serve ok"

echo "--- export: the example lab as a static site ---"
( cd "$LAB" && ckit export --out "$TMP/site" --base /lab-kit/ >/dev/null ) || fail "ckit export failed"
for f in index.html shell/dashboard.html shell/theme.css content/ladder.json content/stories/nearly-sorted/index.html \
         record/findings.md experiments/20260901-e1-nearly-sorted/PROBE.md; do
  [ -e "$TMP/site/$f" ] || fail "export lacks $f"
done
grep -q 'url=/lab-kit/content/projects/sorting-crossover/' "$TMP/site/index.html" || fail "the exported index does not lead to the front door"
mkdir -p "$TMP/pages" && mv "$TMP/site" "$TMP/pages/lab-kit"
python3 -m http.server "$SPORT" -d "$TMP/pages" -b 127.0.0.1 >/dev/null 2>&1 & HTTPD=$!
sleep 0.8
curl -fsS "http://127.0.0.1:$SPORT/lab-kit/shell/dashboard.html" | grep -q 'href="/lab-kit/shell/lib.css"' || fail "the exported dashboard is not rebased"
curl -fsS "http://127.0.0.1:$SPORT/lab-kit/content/ladder.json" | grep -q '"F-1"' || fail "the exported ladder.json is not served"
kill "$HTTPD"; HTTPD=""
echo "export ok"

echo "--- kit drift is detected, and re-sync repairs it ---"
echo "# tampered" >> "$LAB/kit/DISCIPLINE.md"
( cd "$LAB" && make kit-verify >/dev/null 2>&1 ) && fail "tampering with the vendored kit was NOT detected"
( cd "$LAB" && LAB_KIT="$KIT" make kit-sync >/dev/null && make kit-verify >/dev/null ) || fail "re-sync did not repair"
echo "drift ok"

echo "--- library mode ---"
json_set "$LAB/kit.json" 'c["ladder"] = "off"'
OUT="$( cd "$LAB" && python3 kit/tools/ladder_lint.py 2>&1 )"
echo "$OUT" | grep -q "library mode" || fail "ladder=off did not enter library mode"
json_set "$LAB/kit.json" 'c["ladder"] = "strict"'
echo "library mode ok"

echo "e2e ok"
