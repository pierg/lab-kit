"""The dashboard's data: the record as a status board, generated — never authored.

A content-kit generator (kit.json `generators`), registered by lab-kit's install.sh when the lab
opts in with `"dashboard": true`. `ckit lint` / `ckit nav` write `content/ladder.json`, `ckit check`
fails when it drifts, and `/shell/dashboard.html` (a lab-kit shell page) renders it. Nobody writes
it, so it cannot drift from the files it points at.

The chronicle renders the record as a *timeline* — how we got here. The ladder renders it as a
*status board* — what is true now:

  now          the top of the first record file whose title says "State"
  questions    QUESTIONS.md's Q<n> headings, their status and kill criterion   (chronicle_lab)
  experiments  every pre-registration, newest lock first, with its findings    (chronicle_lab)
  findings     record/findings.md's rows: id, title, status                   (chronicle_lab)
  claims       record/claims.md's rows and the findings each rests on         (chronicle_lab)
  decisions    the chronicle's own decision / kill / pivot events, most recent first
  counts       tallies by status

Schema (content/ladder.json):
    now?        {title, summary, href, path}
    questions[] {id, title, status, kill, href}
    experiments[] {slug, title, question, locked, status, kill_rule, href, findings[], supersedes, superseded_by}
    findings[]  {id, title, status, href}
    claims[]    {id, title, rests_on[], href}
    decisions[] {date, kind, title, summary, href}
    counts      {findings:{<status>:n}, experiments:{<status>:n}, questions:{<status>:n}, claims:n}

Runs inside the engine, which is why it may import `ckit.chronicle` (for the generic record
catalogue and the merged timeline); the lab's own vocabulary comes from chronicle_lab.py beside it.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

DECISION_KINDS = ("decision", "kill", "pivot")
DECISION_LIMIT = 16
OUT = "content/ladder.json"


def _chronicle_lab():
    p = Path(__file__).resolve().parent / "chronicle_lab.py"
    spec = importlib.util.spec_from_file_location("lab_chronicle_for_ladder", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def enabled(cfg: dict) -> bool:
    """Opt-in: the lab asks for its dashboard with `"dashboard": true`, or makes it the front door."""
    return cfg.get("dashboard") is True or cfg.get("home") in ("dashboard", "dashboard.html")


def _strip_status_suffix(title: str) -> str:
    for w in ("LIVE", "DRAFT", "HISTORICAL", "FROZEN", "PARKED", "RETIRED"):
        marker = f" — {w}"
        if title.endswith(marker):
            return title[: -len(marker)].strip()
    return title


def _now(repo) -> dict | None:
    """The current phase — the top of the first record file whose title says State."""
    from ckit import chronicle
    from ckit.text import normalize
    for r in chronicle.record_catalog(repo):
        if "state" not in r["title"].lower():
            continue
        p = repo.root / r["path"]
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return None
        title, i = _strip_status_suffix(r["title"]), 0
        for i, ln in enumerate(lines):
            if ln.startswith("# "):
                break
        buf: list[str] = []
        for ln in lines[i + 1:]:
            s = ln.strip()
            if s.startswith("#"):
                break
            if not s or s.startswith("**Status"):
                if buf:
                    break
                continue
            buf.append(s)
            if len(buf) >= 2:
                break
        summary = normalize(" ".join(buf).replace("*", "").replace("`", ""))[:320]
        return {"title": title, "summary": summary, "href": r["href"], "path": r["path"]}
    return None


def _counts(findings: list, experiments: list, questions: list, claims: list) -> dict:
    def by_status(rows: list) -> dict:
        tally: dict[str, int] = {}
        for r in rows:
            k = (r.get("status") or "—")
            tally[k] = tally.get(k, 0) + 1
        return tally

    return {
        "findings": by_status(findings),
        "experiments": by_status(experiments),
        "questions": by_status(questions),
        "claims": len(claims),
    }


def build(repo) -> dict:
    from ckit import chronicle
    lab = _chronicle_lab()
    chron = chronicle.build(repo)
    rows = lab.ladder(repo.root, repo.cfg)
    decisions = [
        {"date": e["date"], "kind": e["kind"], "title": e["title"],
         "summary": e.get("summary", ""), "href": e["href"]}
        for e in chron["events"] if e["kind"] in DECISION_KINDS
    ][:DECISION_LIMIT]
    findings = [x for x in rows["findings"] if isinstance(x, dict) and x.get("id")]
    questions = [x for x in rows["questions"] if isinstance(x, dict) and x.get("id")]
    claims = [x for x in rows["claims"] if isinstance(x, dict) and x.get("id")]
    experiments = lab.experiments(repo.root, repo.cfg)
    return {
        "version": 1,
        "now": _now(repo),
        "questions": questions,
        "experiments": experiments,
        "findings": findings,
        "claims": claims,
        "decisions": decisions,
        "counts": _counts(findings, experiments, questions, claims),
    }


def generate(repo) -> dict:
    """content-kit's generator hook: nothing unless the lab opted in and declares a record."""
    from ckit import chronicle
    if not enabled(repo.cfg) or not chronicle.enabled(repo):
        return {}
    return {OUT: build(repo)}
