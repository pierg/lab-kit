"""`lab-kit experiment`, `lab-kit lock` and `lab-kit score`: an experiment's folder, its lock and its scorecard."""

from __future__ import annotations

from folio.checks.run import run as folio_run
from folio.util import is_slug

from .. import protocol as protocol_mod
from .. import records
from ..errors import LabError
from ..lab import Lab

GITIGNORE = "# A run's scratch and log stay out of git; out/ is committed once, at the end.\nruns/*/work/\nruns/*/run.log\n"


def experiment(lab: Lab, slug: str) -> list[str]:
    if not is_slug(slug):
        raise LabError(f"`{slug}` is not a slug: lowercase letters, digits and single hyphens")
    proto = protocol_mod.require(lab, slug)
    folder = lab.experiments / proto.slug
    if folder.exists():
        raise LabError(f"experiments/{proto.slug}/ exists already")
    (folder / "bin").mkdir(parents=True)
    (folder / "runs").mkdir()
    (folder / "bin" / ".gitkeep").touch()
    (folder / "runs" / ".gitkeep").touch()
    (folder / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    base = f"experiments/{proto.slug}"
    return [f"created {base}/bin/", f"created {base}/runs/", f"created {base}/.gitignore"]


def lock(lab: Lab, slug: str) -> list[str]:
    proto = protocol_mod.require(lab, slug)
    if proto.status != "locked":
        raise LabError(f"{proto.path} has status `{proto.status}`; set it to `locked` through folio's write "
                       "skill first")
    folder = lab.experiments / proto.slug
    if not folder.is_dir():
        raise LabError(f"experiments/{proto.slug}/ does not exist; run `lab-kit experiment {proto.slug}` first")
    path = records.lock_path(lab, proto.slug)
    if path.exists():
        raise LabError(f"experiments/{proto.slug}/{records.LOCK} exists already: a protocol is locked once")
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
    })
    return [f"created experiments/{proto.slug}/{records.LOCK}"]



def score(lab: Lab, slug: str) -> list[str]:
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
        "# `evidence` is a path from the lab root, inside a finished run.",
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
