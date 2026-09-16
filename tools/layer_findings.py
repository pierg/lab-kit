#!/usr/bin/env python3
"""layer_findings.py — split a findings ledger's long rows into interface rows + defense files.

    python3 layer_findings.py --lab <root> --drafts drafts.json --date 2026-09-16 [--dry-run DIR]
    python3 layer_findings.py --selftest

The row is the interface (LADDER.md, "The row is the interface"); its defense — the row's existing
long text — moves VERBATIM to record/findings/F-<n>.md. The interface fields (headline, number,
bound, why, tier, status note, primary anchors) come from a drafts JSON produced upstream (drafted,
independently verified, mechanically bound-checked). Everything else — the Re-derive command, the
bank date (git first-appearance of the ORIGINAL heading), row order, sub-row nesting — is taken from
the ledger itself, deterministically.

Fail loud: a row without a draft, a draft that invents an anchor, a headline that carries an id, a
missing Re-derive, an undatable row, or a defense file that does not contain the original body
verbatim aborts the whole run before anything is written.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# The same four separators chronicle_lab.ROW accepts. A heading this misses is not a row: its
# fields land in the previous row's body, where last-wins would silently replace that row's own.
HEAD = re.compile(r"^(#{2,3})\s+(F-\d+(?:\.\d+)*)\s*[·—–-]\s*(.+?)\s*$")
ROWISH = re.compile(r"^#{2,3}\s+F-\d")  # looks like a row heading, whatever it turns out to be
FIELD = re.compile(r"^\*\*(Status|Anchor|Re-derive):\*\*\s*(.+)$")
BACKTICKED = re.compile(r"`([^`]+)`")
STATUSES = ("BANKED", "PROVISIONAL", "RETRACTED", "SUPERSEDED", "MOVED")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def is_iso(s: str) -> bool:
    """YYYY-MM-DD *and* a real calendar day — `2026-13-45` is the right shape and no day at all."""
    if not ISO.match(s or ""):
        return False
    try:
        date.fromisoformat(s)
    except ValueError:
        return False
    return True


def git_env() -> dict[str, str]:
    """The environment minus git's own repository pointers — a hook or a `git rebase --exec`
    exports GIT_DIR / GIT_WORK_TREE / GIT_INDEX_FILE, and every git below would then read, and
    in the selftest write, that repository instead of the lab."""
    return {k: v for k, v in os.environ.items()
            if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")}


# --- the voice proxies (the same bounds the drafting workflow enforced; re-checked here, deterministically)
ID = re.compile(r"\b[FC]-\d|§|\bdsl:", re.I)
PATHISH = re.compile(r"(experiments|record|harness|ops|content)/|\.(tsv|md|py|sh|json)\b|(?=[0-9a-f]*[a-f])\b[0-9a-f]{7,}\b")
CODEY = re.compile(r"(?<![\w-])(E\d[ab]?|C\d'{0,2}|D\d(?:\.\d)?|M\d|Q\d|T\d|G\d|B\d)(?![\w'])")
LIMITS = {"headline": 24, "bound": 60, "why": 45, "number": 30, "tier": 20, "status_note": 12}


@dataclass
class Row:
    level: int
    id: str
    title: str
    heading: str
    start: int                      # 1-based line of the heading
    body: list[str] = field(default_factory=list)
    fields: dict[str, str] = field(default_factory=dict)


def words(s: str) -> int:
    return len((s or "").split())


def parse_ledger(text: str) -> tuple[list[str], list[Row]]:
    """Header lines (before the first row) and the rows in file order, sub-rows included."""
    lines = text.split("\n")
    header: list[str] = []
    rows: list[Row] = []
    cur: Row | None = None
    for i, ln in enumerate(lines, 1):
        m = HEAD.match(ln)
        if m:
            cur = Row(level=len(m.group(1)), id=m.group(2), title=m.group(3), heading=ln, start=i)
            rows.append(cur)
            continue
        if cur is None:
            header.append(ln)
        else:
            cur.body.append(ln)
    for r in rows:
        r.fields = {m.group(1): m.group(2).strip() for m in (FIELD.match(x) for x in r.body) if m}
    return header, rows


def git_first_date(root: Path, rel: str, heading: str) -> str:
    out = subprocess.run(
        ["git", "log", "--reverse", "--format=%cs", "-S", heading, "--", rel],
        cwd=root, env=git_env(), capture_output=True, text=True, check=False,
    ).stdout.strip().split("\n")
    return out[0].strip() if out and out[0].strip() else ""


def load_drafts(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["rows"] if "rows" in data else [r for g in data["groups"] for r in g["rows"]]
    out: dict[str, dict] = {}
    for r in rows:
        if r["id"] in out:
            raise SystemExit(f"layer_findings: duplicate draft for {r['id']}")
        out[r["id"]] = r
    return out


def check_draft(r: Row, d: dict) -> list[str]:
    v: list[str] = []
    for k, lim in LIMITS.items():
        if words(d.get(k, "")) > lim:
            v.append(f"{k} is {words(d[k])} words; limit {lim}")
    for k in ("headline", "bound", "why", "status_note"):
        s = d.get(k, "")
        if ID.search(s):
            v.append(f"{k} carries a finding/claim id")
        if k != "status_note" and PATHISH.search(s):
            v.append(f"{k} carries a path or commit hash")
    for k in ("headline", "why"):
        if CODEY.search(d.get(k, "")):
            v.append(f"{k} carries a rung/mission code")
    if d.get("status_word") not in STATUSES:
        v.append(f"status_word {d.get('status_word')!r} not in {STATUSES}")
    if not d.get("headline", "").strip():
        v.append("headline is empty")
    anchors = d.get("anchor_primary") or []
    original = set(BACKTICKED.findall(r.fields.get("Anchor", "")))
    if not 1 <= len(anchors) <= 3:
        v.append("anchor_primary must hold 1-3 entries")
    for a in anchors:
        if a.strip("`") not in original:
            v.append(f"anchor {a!r} is not an anchor of the original row")
    if "Re-derive" not in r.fields:
        v.append("original row has no Re-derive field")
    return v


def render_row(r: Row, d: dict, date: str, defense_rel: str) -> list[str]:
    status = d["status_word"] + (f" · {d['status_note'].strip()}" if d.get("status_note", "").strip() else "")
    return [
        f"{'#' * r.level} {r.id} · {d['headline'].strip().rstrip('.')}",   # a heading carries no full stop
        f"**Status:** {status}",
        f"**Tier:** {d['tier'].strip()}",
        f"**Date:** {date}",
        f"**Number:** {d['number'].strip()}",
        f"**Bound:** {d['bound'].strip()}",
        f"**Why it matters:** {d['why'].strip()}",
        f"**Anchor:** {' · '.join(a.strip() for a in d['anchor_primary'])}",
        f"**Re-derive:** {r.fields['Re-derive']}",
        f"**Defense:** `{defense_rel}`",
        "",
    ]


def render_defense(r: Row, date: str, migrated_on: str, tag: str) -> str:
    head = [
        f"# {r.id} · {r.title} — defense",
        "",
        f"**Status: LIVE** — the defense of finding `{r.id}` (banked {date}); its interface row is `{r.id}` in `record/findings.md`. "
        f"Moved here verbatim on {migrated_on} by the record-layering migration (tree before: tag `{tag}`); nothing below was edited. "
        "Corrections are dated additions at the end, never edits in place.",
        "",
        "---",
        "",
    ]
    # the row's content lines stay byte-exact; only the blank separator lines that trailed the row in
    # the ledger are dropped, so the file ends with exactly one newline (the file gate refuses more)
    return "\n".join(head + content_lines(r)) + "\n"


def content_lines(r: Row) -> list[str]:
    body = list(r.body)
    while body and body[-1] == "":
        body.pop()
    return body


LAYERED_NOTE = (
    "**Layered rows ({date}).** Each row is the *interface*: a plain headline, the number, its bound in one sentence, "
    "why it matters, status, tier, bank date, the primary anchor, the re-derivation command, and a `Defense:` link. "
    "The *defense* — the row's full original text: licensed sentence, long-form scope bound, predictions as scored, "
    "reviewer verdict, anomalies, disclosures, dated annotations — lives verbatim at `record/findings/F-<n>.md` and is "
    "never summarized back into the row. Rows banked before this date were split by the disclosed migration recorded in "
    "`record/logbook/lab.md` ({date}); the tree before it is tag `{tag}`."
)


def assemble(root: Path, drafts: dict[str, dict], migrated_on: str, tag: str,
             ledger_rel: str = "record/findings.md", defense_dir: str = "record/findings") -> tuple[str, dict[str, str], dict]:
    text = (root / ledger_rel).read_text(encoding="utf-8")
    header, rows = parse_ledger(text)
    if not rows:
        raise SystemExit("layer_findings: no rows found")
    problems: list[str] = []
    # A heading that looks like a row but does not parse as one, a field key that appears twice in
    # a single body, and a draft no row consumed are the three faces of the same failure: a row
    # boundary the parser did not see. Each is silent without these checks.
    problems += [f"heading I cannot read: {ln.strip()[:70]!r}"
                 for ln in text.split("\n") if ROWISH.match(ln) and not HEAD.match(ln)]
    orphans = sorted(set(drafts) - {r.id for r in rows})
    if orphans:
        problems.append("drafts no row consumed: " + ", ".join(orphans))
    dates: dict[str, str] = {}
    for r in rows:
        keys = [m.group(1) for m in (FIELD.match(x) for x in r.body) if m]
        dupes = sorted({k for k in keys if keys.count(k) > 1})
        if dupes:
            problems.append(f"{r.id}: {', '.join(dupes)} appears twice in one row body")
        d = drafts.get(r.id)
        if d is None:
            problems.append(f"{r.id}: no draft")
            continue
        problems += [f"{r.id}: {p}" for p in check_draft(r, d)]
        dates[r.id] = git_first_date(root, ledger_rel, r.heading)
        if not is_iso(dates[r.id]):
            problems.append(f"{r.id}: bank date not recoverable from git for heading {r.heading[:60]!r}")
    if problems:
        raise SystemExit("layer_findings: refusing to write —\n  " + "\n  ".join(problems))

    out_lines = list(header)
    # the layered-rows note goes right before the header's closing rule, so the ledger explains its own shape
    note = LAYERED_NOTE.format(date=migrated_on, tag=tag)
    if "---" in out_lines:
        k = len(out_lines) - 1 - out_lines[::-1].index("---")
        out_lines[k:k] = [note, ""]
    else:
        out_lines += [note, ""]
    defenses: dict[str, str] = {}
    for r in rows:
        rel = f"{defense_dir}/{r.id}.md"
        out_lines += render_row(r, drafts[r.id], dates[r.id], rel)
        defenses[rel] = render_defense(r, dates[r.id], migrated_on, tag)
        body = "\n".join(content_lines(r))
        if body not in defenses[rel]:
            raise SystemExit(f"layer_findings: {r.id} body is not verbatim in its defense file")
    new_text = "\n".join(out_lines).rstrip("\n") + "\n"
    stats = {
        "rows": len(rows),
        "words_before": words(text),
        "words_after": words(new_text),
        "per_row_after": {r.id: words("\n".join(render_row(r, drafts[r.id], dates[r.id], ""))) for r in rows},
        "dates": dates,
    }
    return new_text, defenses, stats


def write_out(root: Path, new_text: str, defenses: dict[str, str], ledger_rel: str = "record/findings.md") -> None:
    # Everything is checked before anything is written: a refusal half-way through would leave a
    # rewritten ledger pointing at defense files that were never created.
    taken = sorted(rel for rel in defenses if (root / rel).exists())
    if taken:
        raise SystemExit("layer_findings: refusing to overwrite an existing defense file — " + ", ".join(taken))
    ledger = root / ledger_rel
    if not os.access(ledger.parent, os.W_OK) or (ledger.exists() and not os.access(ledger, os.W_OK)):
        raise SystemExit(f"layer_findings: {ledger_rel} is not writable")
    ledger.write_text(new_text, encoding="utf-8")
    for rel, body in defenses.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")


# ----------------------------------------------------------------------------- selftest

FIXTURE = """# Findings — LIVE

Header paragraph.

**Conventions.** Anchors are relative to this repo.

---

## F-1 · A very long original headline that names F-0 and says far more than twenty-four words would ever allow in a plain headline
**Status:** BANKED — with a note · **Tier:** reviewer-gated
**Anchor:** `experiments/x/out/a.tsv` · `experiments/x/PROBE.md`
**Re-derive:** `cat experiments/x/out/a.tsv`

**Licensed sentence: seven of nine.** Long prose with a Correction (2026-01-02) that narrows it.


## F-2 — Umbrella of two
**Status:** BANKED (umbrella) · **Tier:** declares its own tier
**Anchor:** `record/x.md`
**Re-derive:** `grep -c x record/x.md`

Umbrella preamble.

### F-2.1 · A sub-row
**Status:** PROVISIONAL · **Tier:** lab finding
**Anchor:** `experiments/y/out/b.tsv`
**Re-derive:** `wc -l experiments/y/out/b.tsv`

**Licensed sentence: three of four.** Bound: one core.
"""

DRAFTS = {"rows": [
    {"id": "F-1", "headline": "Seven of nine pairs closed under the plain loop", "number": "7 of 9 pairs",
     "bound": "One core, one model; says nothing about other cores.", "why": "It sets the floor the ladder is measured against.",
     "status_word": "BANKED", "status_note": "corrected 2026-01-02", "tier": "reviewer-gated",
     "anchor_primary": ["`experiments/x/out/a.tsv`"], "notes": ""},
    {"id": "F-2", "headline": "Two harness-engineering results imported from the earlier ledger", "number": "—",
     "bound": "An umbrella; each sub-row carries its own bound.", "why": "It closes the gap the earlier ledger left.",
     "status_word": "BANKED", "status_note": "", "tier": "declares its own tier", "anchor_primary": ["`record/x.md`"], "notes": ""},
    {"id": "F-2.1", "headline": "Three of four sealed properties proved", "number": "3 of 4",
     "bound": "One core.", "why": "Shows sealed difficulty is judge-relative.", "status_word": "PROVISIONAL", "status_note": "",
     "tier": "lab finding", "anchor_primary": ["`experiments/y/out/b.tsv`"], "notes": ""},
]}


def _seed(root: Path, text: str) -> Path:
    """A ledger in its own git repo — the bank dates come out of history, so history is the fixture.

    `-c commit.gpgsign=false` and `--no-verify` because a host gitconfig that signs every commit,
    or a global hooks path, would otherwise turn this selftest into an unhandled crash.
    """
    (root / "record").mkdir(parents=True)
    (root / "record/findings.md").write_text(text, encoding="utf-8")
    base = ["git", "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
    subprocess.run(["git", "init", "-q"], cwd=root, env=git_env(), check=True)
    subprocess.run([*base, "add", "-A"], cwd=root, env=git_env(), check=True)
    subprocess.run([*base, "commit", "--no-verify", "-qm", "seed"], cwd=root, env=git_env(), check=True)
    return root


def selftest() -> None:
    fails: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        root = _seed(Path(td) / "lab", FIXTURE)
        new_text, defenses, stats = assemble(root, load_drafts_obj(DRAFTS), "2026-09-16", "pre-layering-test")
        if stats["rows"] != 3:
            fails.append(f"expected 3 rows, got {stats['rows']}")
        if set(defenses) != {"record/findings/F-1.md", "record/findings/F-2.md", "record/findings/F-2.1.md"}:
            fails.append(f"defense set wrong: {sorted(defenses)}")
        if "**Licensed sentence: seven of nine.** Long prose with a Correction (2026-01-02) that narrows it." not in defenses["record/findings/F-1.md"]:
            fails.append("F-1 body not verbatim in defense")
        if "### F-2.1 · Three of four sealed properties proved" not in new_text:
            fails.append("sub-row heading level not preserved")
        if "**Status:** BANKED · corrected 2026-01-02" not in new_text:
            fails.append("status note not rendered")
        if "**Defense:** `record/findings/F-2.1.md`" not in new_text:
            fails.append("defense link missing")
        if "**Layered rows (2026-09-16).**" not in new_text or new_text.index("Layered rows") > new_text.index("## F-1"):
            fails.append("layered-rows note missing or after the first row")
        if not all(is_iso(d) for d in stats["dates"].values()):
            fails.append(f"dates not recovered: {stats['dates']}")
        # F-2's heading is punctuated with an em dash: it must parse as its own row, and its
        # fields must stay its own. Absorbed into F-1's body, last-wins would hand F-1 F-2's
        # anchor and re-derivation, and the run would still exit 0.
        if "**Anchor:** `experiments/x/out/a.tsv`" not in new_text or "**Anchor:** `record/x.md`" not in new_text:
            fails.append("an em-dash heading did not parse as its own row: fields were merged")
        # negatives: an id in a headline, an invented anchor, a missing draft — each must refuse
        bad = json.loads(json.dumps(DRAFTS))
        bad["rows"][0]["headline"] = "Seven of nine, see F-0"
        _expect_refusal(root, bad, "id in headline", "carries a finding/claim id", fails)
        bad = json.loads(json.dumps(DRAFTS))
        bad["rows"][2]["anchor_primary"] = ["`experiments/y/out/invented.tsv`"]
        _expect_refusal(root, bad, "invented anchor", "is not an anchor of the original row", fails)
        bad = json.loads(json.dumps(DRAFTS))
        bad["rows"].pop(1)
        _expect_refusal(root, bad, "missing draft", "F-2: no draft", fails)
        bad = json.loads(json.dumps(DRAFTS))
        bad["rows"].append(dict(bad["rows"][0], id="F-404"))
        _expect_refusal(root, bad, "unconsumed draft", "drafts no row consumed: F-404", fails)
        # ...and the two shapes of an unseen row boundary, in the ledger rather than the drafts
        unreadable = _seed(Path(td) / "unreadable", FIXTURE.replace("## F-2 —", "## F-2:"))
        _expect_refusal(unreadable, DRAFTS, "unreadable heading", "heading I cannot read", fails)
        twice = _seed(Path(td) / "twice", FIXTURE.replace(
            "**Re-derive:** `grep -c x record/x.md`",
            "**Re-derive:** `grep -c x record/x.md`\n**Anchor:** `record/y.md`"))
        _expect_refusal(twice, DRAFTS, "duplicate field key", "Anchor appears twice in one row body", fails)

        # writing is all-or-nothing: one existing defense file refuses the whole run, and the
        # ledger it would have rewritten is byte-unchanged afterwards
        write_out(root, new_text, defenses)
        ledger = root / "record/findings.md"
        before = ledger.read_bytes()
        ledger.write_bytes(b"# Findings - LIVE\n\nnot yet migrated\n")
        try:
            write_out(root, new_text, defenses)
            fails.append("overwrite of an existing defense file was not refused")
        except SystemExit:
            if ledger.read_bytes() != b"# Findings - LIVE\n\nnot yet migrated\n":
                fails.append("a refused run still rewrote the ledger")
        ledger.write_bytes(before)
    if fails:
        print("layer_findings selftest FAILED:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("layer_findings selftest ok (assembly, verbatim, nesting, dates, em-dash heading, "
          "6 refusals: id in headline · invented anchor · missing draft · unconsumed draft · "
          "unreadable heading · duplicate field key, and an all-or-nothing write)")


def load_drafts_obj(obj: dict) -> dict[str, dict]:
    return {r["id"]: r for r in obj["rows"]}


def _expect_refusal(root: Path, drafts_obj: dict, what: str, because: str, fails: list[str]) -> None:
    """Refused, and refused *for the stated reason* — every refusal here raises the same SystemExit,
    so a fixture that trips a different check would otherwise pass while testing nothing."""
    try:
        assemble(root, load_drafts_obj(drafts_obj), "2026-09-16", "t")
        fails.append(f"{what}: was not refused")
    except SystemExit as e:
        if because not in str(e):
            fails.append(f"{what}: refused, but not for {because!r} — {e}")


# ----------------------------------------------------------------------------- entry point

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lab", type=Path, help="lab root (contains record/findings.md)")
    ap.add_argument("--drafts", type=Path, help="drafts JSON from the layering workflow")
    ap.add_argument("--date", default="", help="migration date, YYYY-MM-DD (stamped into the note and the defense files)")
    ap.add_argument("--tag", default="", help="git tag of the tree before the migration")
    ap.add_argument("--dry-run", type=Path, help="write the result under this directory instead of the lab")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if not (a.lab and a.drafts and is_iso(a.date) and a.tag):
        raise SystemExit("layer_findings: --lab, --drafts, --date YYYY-MM-DD and --tag are required")
    new_text, defenses, stats = assemble(a.lab, load_drafts(a.drafts), a.date, a.tag)
    target = a.dry_run or a.lab
    if a.dry_run:
        (target / "record").mkdir(parents=True, exist_ok=True)
        for rel in defenses:
            (target / rel).parent.mkdir(parents=True, exist_ok=True)
            if (target / rel).exists():
                (target / rel).unlink()
    write_out(target, new_text, defenses)
    print(json.dumps({k: v for k, v in stats.items() if k != "per_row_after"}, indent=1))
    print("per-row interface words:", " ".join(f"{k}={v}" for k, v in stats["per_row_after"].items()))
    print(f"wrote {target / 'record/findings.md'} and {len(defenses)} defense files under {target / 'record/findings'}")


if __name__ == "__main__":
    main()
