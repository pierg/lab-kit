"""`lab-kit experiment`, `lab-kit lock` and `lab-kit score`: an experiment's folder, its lock and its scorecard."""

from __future__ import annotations

import datetime as _dt

from folio.checks.run import run as folio_run
from folio.util import is_slug

from .. import protocol as protocol_mod
from .. import records
from ..errors import LabError
from ..lab import Lab

def experiment_id(slug: str, day: _dt.date | None = None) -> str:
    """`<YY-MM-DD>-e_<slug>`: the day the experiment was created (UTC), and its protocol's slug."""
    day = day or _dt.datetime.now(_dt.timezone.utc).date()
    return f"{day.strftime('%y-%m-%d')}-e_{slug}"


def experiment(lab: Lab, slug: str) -> list[str]:
    if not is_slug(slug):
        raise LabError(f"`{slug}` is not a slug: lowercase letters, digits and single hyphens")
    proto = protocol_mod.require(lab, slug)
    existing = lab.experiment_for(proto.slug)
    if existing:
        raise LabError(f"experiments/{existing}/ exists already")
    ident = experiment_id(proto.slug)
    folder = lab.experiments / ident
    (folder / "bin").mkdir(parents=True)
    (folder / "bin" / ".gitkeep").touch()
    return [f"created experiments/{ident}/bin/; its runs will be under runs/{ident}/"]


def lock(lab: Lab, slug: str) -> list[str]:
    proto = protocol_mod.require(lab, slug)
    if proto.status != "locked":
        raise LabError(f"{proto.path} has status `{proto.status}`; set it to `locked` through folio's write "
                       "skill first")
    ident = lab.experiment_for(proto.slug)
    if ident is None:
        raise LabError(f"no experiments/<YY-MM-DD>-e_{proto.slug}/; run `lab-kit experiment {proto.slug}` first")
    folder = lab.experiments / ident
    path = folder / records.LOCK
    if path.exists():
        raise LabError(f"experiments/{ident}/{records.LOCK} exists already: a protocol is locked once")
    main = proto.doc.main
    errors = [p for p in folio_run(lab.library()) if p.severity == "error" and main is not None
              and p.path == main.path]
    if errors:
        raise LabError(f"{proto.path} does not pass the gate:\n" + "\n".join(f"  {p.line()}" for p in errors))
    protocol_mod.pinned_config(proto.text(), proto.path)
    protocol_mod.scored_ids(proto.text(), proto.path)
    records.write_json(path, {
        "protocol": proto.slug,
        "path": proto.path,
        "sha256": protocol_mod.hash_text(proto.text()),
        "locked": records.now(),
        "instrument": records.instrument_hash(folder / "bin"),
        **records.provenance(lab.root),
    })
    return [f"created experiments/{ident}/{records.LOCK}"]



def score(lab: Lab, slug: str) -> list[str]:
    if not (lab.experiments / slug).is_dir():
        slug = lab.experiment_for(slug) or slug
    lock_record = records.read_lock(lab, slug)
    if lock_record is None:
        raise LabError(f"experiments/{slug}/{records.LOCK} does not exist: only a locked experiment is scored")
    proto = protocol_mod.require(lab, lock_record.protocol)
    path = records.score_path(lab, slug)
    if path.exists():
        raise LabError(f"experiments/{slug}/{records.SCORE} exists already")
    ids = protocol_mod.scored_ids(proto.text(), proto.path)
    lines = [
        f"# The scorecard of experiment {slug}, against its lock.",
        f"# A prediction's verdict: {', '.join(records.PREDICTION_VERDICTS)}.",
        f"# A decision rule's verdict: {', '.join(records.RULE_VERDICTS)}.",
        "# `evidence` is a path from the lab root, inside a finished run: runs/<experiment>/<run id>/...",
        f"protocol: {proto.slug}",
        f"lock: {lock_record.sha256}",
        "review:            # the independent reviewer's pass: `pass` or `fail`, and where its verdict is recorded",
        '  verdict: ""',
        '  record: ""',
        "scores:",
    ]
    for ident in ids:
        lines += [f"  {ident}:", '    verdict: ""', '    value: ""', '    evidence: ""']
    lines += [
        "# The numbers to record as results, each keyed by a short name, with the result's fields:",
        "# title, protocol, number, baseline, bound, evidence, rederive.",
        "record: {}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return [f"created experiments/{slug}/{records.SCORE} with {len(ids)} ids to score: {', '.join(ids)}"]
