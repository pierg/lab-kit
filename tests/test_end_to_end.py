"""From `lab-kit init` in a fresh repository to a recorded result and a passing gate."""

from __future__ import annotations

import json
import os
from pathlib import Path

from conftest import commit, init_repo

PROTOCOL = """\
---
title: Doubling the input doubles the count
description: Varies the input size, and counts the lines a counter reads.
genre: protocol
status: draft
question: Q-1
---

## Hypothesis

The counter reads every line once.

## Intuition

It reads line by line, so the count follows the size. If it fails, it skips blank lines.

## The one variable

The number of lines. Arms: 10 and 20.

## Held fixed

The same counter, the same text.

## Pinned configuration

```yaml
lines: [10, 20]
budget: none
```

## Allowed moves

Nothing under test makes moves.

## Measures

Lines counted per arm.

## Decision rules

- D1: keep the hypothesis if the count equals the size in both arms.
- D2 (kill): drop it if any arm differs.

## Predictions

- P1: both arms count exactly. Confidence: 90%.

## What it cannot show

Anything about files with no line ending.
"""

COUNTER = """\
import os, sys
from pathlib import Path
if sys.argv[1:] == ["--selftest"]:
    assert len("a\\nb\\n".splitlines()) == 2
    print("selftest passed")
    raise SystemExit(0)
if sys.argv[1:2] == ["--fold"]:
    print(sum(1 for _ in Path(sys.argv[2]).read_text().splitlines()))
    raise SystemExit(0)
out = Path(os.environ["LAB_OUT"])
(out / "lines.txt").write_text("".join(f"line {i}\\n" for i in range(20)))
"""

QUESTION = """\
---
title: Does the counter read every line?
description: The answer says whether its counts can be trusted.
genre: question
id: Q-1
rank: 1
---

## Why it matters

Every count depends on it.

## What would settle it

Counting known files.

## What would make us drop it

Nothing to count.

## Answer

Not yet.
"""

MAP = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Work</title>
<meta name="genre" content="map">
<meta name="title" content="Work">
<meta name="description" content="The lab's question and its work.">
</head>
<body>
<main>
<ul class="rows">
<li><a href="/content/questions/Q-1.md">Does the counter read every line?</a></li>
</ul>
</main>
</body>
</html>
"""


def test_init_to_recorded_result(tmp_path: Path, monkeypatch, lab_kit, folio) -> None:
    root = tmp_path / "lab"
    root.mkdir()
    init_repo(root)
    docs = root / "docs"
    assert folio(root, "init", "docs", "--name", "Counter lab")[0] == 0
    assert folio(docs, "config", "set", "root", "..")[0] == 0
    monkeypatch.chdir(root)

    code, out = lab_kit("init", "--library", "docs")
    assert code == 0, out
    assert "switched pack `lab` on" in out
    for path in ("lab.yaml", "ops/STATE.md", ".lab/method/DISCIPLINE.md", ".lab/method/LADDER.md",
                 ".agents/skills/plan-mission/SKILL.md", ".agents/skills/run-mission/SKILL.md",
                 ".agents/skills/write/SKILL.md", ".agents/agents/reviewer.md"):
        assert (root / path).is_file(), path
    assert not (root / ".agents/skills/mission").exists()
    assert os.readlink(root / ".claude/agents") == os.path.join("..", ".agents", "agents")
    assert (root / ".claude/agents/scout.md").is_file()

    (docs / "content/maps").mkdir(parents=True)
    (docs / "content/maps/work.html").write_text(MAP, encoding="utf-8")
    (docs / "content/questions").mkdir()
    (docs / "content/questions/Q-1.md").write_text(QUESTION, encoding="utf-8")
    (docs / "content/protocols").mkdir()
    protocol = docs / "content/protocols/line-count.md"
    protocol.write_text(PROTOCOL, encoding="utf-8")
    assert folio(docs, "config", "set", "home.maps", "work")[0] == 0

    assert lab_kit("experiment", "line-count")[0] == 0
    (root / "experiments/line-count/bin/count.py").write_text(COUNTER, encoding="utf-8")
    assert lab_kit("check", "--only", "lab-selftest")[0] == 0

    # No run and no lock record before the lock.
    code, out = lab_kit("run", "line-count", "--", "python3", "x.py")
    assert code == 2 and "no run starts before the lock" in out
    code, out = lab_kit("lock", "line-count")
    assert code == 2 and "has status `draft`" in out

    protocol.write_text(PROTOCOL.replace("status: draft", "status: locked"), encoding="utf-8")
    code, out = lab_kit("lock", "line-count")
    assert code == 0 and "created experiments/line-count/lock.json" in out
    assert lab_kit("lock", "line-count")[0] == 2  # a protocol is locked once
    assert folio(docs, "journal", "add", "--title", "Locked line-count", "--description", "Two arms.",
                 "--body", "Locked.", "--kind", "lock", "--about", "line-count,Q-1")[0] == 0
    assert folio(docs, "index")[0] == 0
    code, out = lab_kit("check")
    assert code == 0, out
    commit(root, "lock")

    code, out = lab_kit("run", "line-count", "--spend", "--", "python3", "x.py")
    assert code == 2 and "names its mission" in out
    code, out = lab_kit("run", "line-count", "--wait", "--", "python3", "experiments/line-count/bin/count.py")
    assert code == 0, out
    run_dir = next((root / "experiments/line-count/runs").glob("2*"))
    record = json.loads((run_dir / "run.json").read_text())
    assert record["exit"] == 0 and record["config"] == {"lines": [10, 20], "budget": "none"}
    assert (run_dir / "MANIFEST.sha256").read_text().endswith("  lines.txt\n")
    assert "finished" in lab_kit("runs")[1]
    commit(root, "run")

    code, out = lab_kit("score", "line-count")
    assert code == 0 and "P1, D1, D2" in out
    score = root / "experiments/line-count/score.yaml"
    evidence = f"experiments/line-count/runs/{run_dir.name}/out/lines.txt"
    (root / "ops/missions").mkdir(exist_ok=True)
    (root / "ops/missions/2026-10-04-count.md").write_text(
        "---\ntitle: Count\nstatus: active\nrests_on: [Q-1]\napproved: \"The operator, 2026-10-04\"\n---\n\n## Log\n\n- 2026-10-04 Reviewer pass: pass.\n", encoding="utf-8")
    text = score.read_text()
    text = text.replace('verdict: ""\n  record: ""', 'verdict: pass\n  record: ops/missions/2026-10-04-count.md#log')
    text = text.replace('verdict: ""', "verdict: HIT", 1).replace('verdict: ""', "verdict: FIRED", 1)
    text = text.replace('verdict: ""', "verdict: NOT FIRED", 1).replace('evidence: ""', f"evidence: {evidence}")
    score.write_text(text)
    assert lab_kit("check", "--only", "lab-score-exact")[0] == 0

    rederive = f"python3 experiments/line-count/bin/count.py --fold {evidence}"
    code, out = folio(docs, "new", "result", "--title", "The counter read 20 lines of 20",
                      "--description", "Lines counted in the larger arm.", "--tags", "counting", "--protocol", "line-count",
                      "--number", "20", "--baseline", "the 20 lines written", "--bound", "One small file.",
                      "--evidence", evidence, "--rederive", rederive)
    assert code == 0, out
    result = docs / "content/results/R-1.md"
    result.write_text(result.read_text().replace("{{One or two sentences.}}", "The counts can be trusted."))
    assert lab_kit("rederive", "R-1") == (0, "R-1: re-derived `20`, its number\n")
    assert folio(docs, "journal", "add", "--title", "Recorded R-1", "--description", "The larger arm.",
                 "--body", "Recorded R-1.", "--about", "R-1,line-count")[0] == 0
    assert folio(docs, "journal", "add", "--title", "The counter reads every line", "--description",
                 "D1 fired; no report, as there is nothing more to say.", "--body", "P1 hit.",
                 "--kind", "lesson", "--about", "line-count")[0] == 0
    assert folio(docs, "index")[0] == 0
    code, out = lab_kit("check")
    assert code == 0, out
    assert out.strip().endswith("0 errors, 0 warnings"), out
    commit(root, "result")
    assert lab_kit("check")[0] == 0


def test_init_needs_a_library_rooted_at_the_lab(tmp_path: Path, monkeypatch, lab_kit, folio) -> None:
    root = tmp_path / "lab"
    root.mkdir()
    init_repo(root)
    monkeypatch.chdir(root)
    code, out = lab_kit("init", "--library", "docs")
    assert code == 2 and "holds no folio.yaml" in out
    assert folio(root, "init", "docs")[0] == 0
    monkeypatch.chdir(root)
    code, out = lab_kit("init", "--library", "docs")
    assert code == 2 and "folio config set root .." in out


def test_init_before_a_library_installs_the_skills(tmp_path: Path, monkeypatch, lab_kit, folio) -> None:
    root = tmp_path / "lab"
    root.mkdir()
    init_repo(root)
    monkeypatch.chdir(root)
    code, out = lab_kit("init")
    assert code == 0 and "read .agents/skills/set-up-lab/SKILL.md" in out
    assert (root / ".agents/skills/set-up-lab/SKILL.md").is_file()
    assert not (root / "lab.yaml").exists()
    # folio's own skills install beside lab-kit's, through the same link.
    assert folio(root, "init", "docs", "--name", "Fresh lab")[0] == 0
    assert (root / ".agents/skills/set-up/SKILL.md").is_file()
    assert (root / ".agents/skills/set-up-lab/SKILL.md").is_file()
    assert folio(root / "docs", "config", "set", "root", "..")[0] == 0
    monkeypatch.chdir(root)
    code, out = lab_kit("init", "--library", "docs")
    assert code == 0 and "created lab.yaml" in out


def test_freeze_needs_a_listed_surface(make_lab, lab_kit) -> None:
    root = make_lab()
    code, out = lab_kit("freeze", "experiments")
    assert code == 2 and "not listed under `frozen:`" in out
    code, out = lab_kit("freeze", "substrate")
    assert code == 0 and "recorded 2 file(s) of substrate" in out


def test_init_again_restores_the_method(make_lab, lab_kit) -> None:
    root = make_lab()
    (root / ".lab/method/LADDER.md").write_text("edited\n", encoding="utf-8")
    code, out = lab_kit("init", "--library", "docs")
    assert code == 0 and "updated .lab/method/LADDER.md" in out
    assert lab_kit("check")[0] == 0
