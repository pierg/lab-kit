"""Checks on results and scores: numbers re-derive, results rest on finished runs, scores match the lock."""

from __future__ import annotations

from pathlib import PurePosixPath

from .. import protocol as protocol_mod
from .. import records
from .. import rederive as rederive_mod
from ..errors import LabError
from ..lab import Lab
from .base import Reporter

SCORE_KEYS = ("protocol", "lock", "review", "scores", "record")
# The journal kinds that can say why a scored experiment has no report.
EXPLAINING_KINDS = ("lesson", "kill", "decision", "pivot")


def _doc_path(lab: Lab, doc) -> str:
    return lab.doc_path(doc.meta_file.path) if doc.meta_file else doc.key


def rederive(lab: Lab, rep: Reporter) -> None:
    """Every live result's re-derive command prints its number exactly."""
    for doc in rederive_mod.live_results(lab):
        outcome = rederive_mod.run(lab, doc)
        if not outcome.ok:
            rep.add(_doc_path(lab, doc), f"{doc.id} does not re-derive: {outcome.detail}")


def read_score(lab: Lab, slug: str) -> dict | None:
    path = records.score_path(lab, slug)
    if not path.is_file():
        return None
    data = records.read_yaml(path, lab.rel(path))
    missing = [k for k in SCORE_KEYS if k not in data]
    if missing:
        raise LabError(f"{lab.rel(path)}: missing {', '.join(missing)}")
    return data


def review_passed(lab: Lab, score: dict) -> str | None:
    """None when the score records a reviewer pass, or why it does not."""
    review = score.get("review")
    if not isinstance(review, dict):
        return "`review` must hold `verdict` and `record`"
    if review.get("verdict") != "pass":
        return f"`review.verdict` is `{review.get('verdict') or ''}`, not `pass`"
    pointer = str(review.get("record") or "").split("#", 1)[0]
    if not pointer:
        return "`review.record` points nowhere: it names the file where the reviewer's verdict is recorded"
    if not (lab.root / pointer).is_file():
        return f"`review.record` points to {pointer}, which does not exist"
    return None


def _inside_finished_run(lab: Lab, slug: str, evidence: str) -> str | None:
    """None when the evidence lies in the out/ folder of a finished run of this experiment, or why not."""
    parts = PurePosixPath(evidence).parts
    if len(parts) < 6 or parts[:2] != ("experiments", slug) or parts[2] != "runs" or parts[4] != "out":
        return f"its evidence `{evidence}` is not inside experiments/{slug}/runs/<run>/out/"
    for run in records.runs(lab, slug):
        if run.run_id == parts[3]:
            if run.state != "finished":
                return f"its evidence is in run {run.run_id}, which is {run.state}, not finished"
            return None
    return f"its evidence names run {parts[3]}, which has no {records.RUN}"


def result_grounded(lab: Lab, rep: Reporter) -> None:
    """Every live result names a locked protocol, its evidence sits in a finished run, and a reviewer passed it."""
    for doc in rederive_mod.live_results(lab):
        where = _doc_path(lab, doc)

        def one(doc=doc, where=where) -> None:
            slug = str(doc.meta.get("protocol", ""))
            proto = protocol_mod.find(lab, slug)
            if proto is None or proto.status not in ("locked", "abandoned"):
                rep.add(where, f"{doc.id} names protocol `{slug}`, which is not a locked protocol")
                return
            slug = proto.slug
            if records.read_lock(lab, slug) is None:
                rep.add(where, f"{doc.id} names protocol `{slug}`, which has no {records.LOCK}")
            why = _inside_finished_run(lab, slug, PurePosixPath(str(doc.meta.get("evidence", ""))).as_posix())
            if why:
                rep.add(where, f"{doc.id}: {why}")
            score = read_score(lab, slug)
            if score is None:
                rep.add(where, f"{doc.id}: experiments/{slug}/{records.SCORE} does not exist, so no reviewer "
                               "pass is recorded")
                return
            why = review_passed(lab, score)
            if why:
                rep.add(where, f"{doc.id}: experiments/{slug}/{records.SCORE} records no reviewer pass: {why}")
        rep.guard(where, one)


def score_exact(lab: Lab, rep: Reporter) -> None:
    """A score names the lock's hash and scores exactly the lock's prediction and rule ids."""
    for slug in lab.experiment_slugs():
        path = f"experiments/{slug}/{records.SCORE}"

        def one(slug=slug, path=path) -> None:
            score = read_score(lab, slug)
            if score is None:
                return
            lock = records.read_lock(lab, slug)
            if lock is None:
                rep.add(path, f"scores experiment `{slug}`, which has no {records.LOCK}")
                return
            if score.get("protocol") != lock.protocol:
                rep.add(path, f"names protocol `{score.get('protocol')}`, not `{lock.protocol}`")
            if score.get("lock") != lock.sha256:
                rep.add(path, "names a lock hash that is not the one in its lock.json")
            proto = protocol_mod.find(lab, lock.protocol)
            if proto is None:
                return
            wanted = protocol_mod.scored_ids(proto.text(), proto.path)
            scores = score.get("scores")
            if not isinstance(scores, dict):
                rep.add(path, "`scores` must map each prediction and rule id to its verdict")
                return
            for ident in wanted:
                if ident not in scores:
                    rep.add(path, f"does not score {ident}, which the lock names")
            for ident, entry in scores.items():
                if ident not in wanted:
                    rep.add(path, f"scores {ident}, which the lock does not name")
                    continue
                allowed = records.PREDICTION_VERDICTS if str(ident).startswith("P") else records.RULE_VERDICTS
                if not isinstance(entry, dict):
                    rep.add(path, f"{ident} must hold `verdict`, `value` and `evidence`")
                    continue
                if entry.get("verdict") not in allowed:
                    rep.add(path, f"{ident} has verdict `{entry.get('verdict') or ''}`; "
                                  f"allowed: {', '.join(allowed)}")
                evidence = str(entry.get("evidence") or "")
                if not evidence:
                    rep.add(path, f"{ident} names no evidence")
                elif not (lab.root / evidence).exists():
                    rep.add(path, f"{ident} names evidence {evidence}, which does not exist")
        rep.guard(path, one)


def scored_reported(lab: Lab, rep: Reporter) -> None:
    """Every scored experiment has a report citing its results, or a journal entry about it saying why not."""
    lib = lab.library()
    for slug in lab.experiment_slugs():
        if not records.score_path(lab, slug).is_file():
            continue
        proto = protocol_mod.find(lab, slug)
        name = proto.slug if proto else slug
        results = [d for d in lib.documents if d.is_a("result")
                   and str(d.meta.get("protocol", "")).casefold() == name.casefold()]
        reported = any(
            any(target in results for link in lib.doc_links(doc) for target in link.docs)
            for doc in lib.documents if doc.is_a("report"))
        if reported:
            continue
        explained = False
        for doc in lib.documents:
            if not doc.is_a("journal") or doc.meta.get("kind") not in EXPLAINING_KINDS:
                continue
            about = doc.meta.get("about") or []
            about = about if isinstance(about, list) else [about]
            if any(str(a).casefold() == name.casefold() for a in about):
                explained = True
                break
        if not explained:
            rep.add(f"experiments/{slug}/{records.SCORE}",
                    f"experiment `{slug}` is scored, but no report cites its results and no journal entry "
                    "about its protocol says why not")
