"""Papers drive the work: the record names no paper, and each active paper's page opens with a scope table whose
included, excluded and open cells `lab check` holds, and whose open row `lab now` puts before the agent."""
import os

from test_flow import experiment, lab, open_question, results
from test_integrity import WRITES, commit, done
from test_states import PAST, git_env

PAGE = """<!DOCTYPE html>
<html><head><title>{title}</title></head>
<body><main>
<p class="thesis">The error falls with the square root of the sample.</p>
<section id="scope"><table><tbody>
<tr><th>Experiments included</th><td data-scope="included">{included}</td></tr>
<tr><th>Experiments excluded / superseded</th><td data-scope="excluded">{excluded}</td></tr>
<tr><th>Open experiments</th><td data-scope="open">{open}</td></tr>
</tbody></table></section>
</main></body></html>
"""


def links(*ids):
    return ", ".join(f'<a href="/lab/{i}/">{i}</a>' for i in ids)


def page(root, path, title="Paper A: The square-root law", included=(), excluded=(), open_=()):
    d = os.path.join(root, "docs", "content", path)
    os.makedirs(d, exist_ok=True)
    open(f"{d}/index.html", "w").write(PAGE.format(title=title, included=links(*included), excluded=links(*excluded), open=links(*open_)))


def papers(root, overview="entries/where-the-results-stand", active=("entries/paper-a",)):
    text = open(f"{root}/lab.toml").read().split("[papers]")[0]
    open(f"{root}/lab.toml", "w").write(text + f'[papers]\noverview = "{overview}"\nactive = [{", ".join(chr(34) + a + chr(34) for a in active)}]\n')


def two_experiments(root):
    """G1.Q1.1 done and confirmed, G1.Q1.2 done and void, G1.Q1.3 still open."""
    open_question(root)
    first, d1, c1 = experiment(root, command=WRITES % "0.5")
    lab(root, "lock", first)
    lab(root, "run", first, "--wait", "--", *c1)
    done(root, first, d1)
    void, d2, c2 = experiment(root, title="Error at 100 and at 1600 flips", command=WRITES % "0.25")
    lab(root, "lock", void)
    lab(root, "run", void, "--wait", "--", *c2)
    results(d2, "0.25")
    lab(root, "review", void, "results", "fail", "The seed was fixed after a first look.")
    later, _, _ = experiment(root, title="Error at 400 and at 1600 flips")
    page(root, "entries/where-the-results-stand", title="Where the results stand")
    return first, void, later


def test_a_lab_without_papers_is_unchanged(tmp_path):
    root = str(tmp_path)
    two_experiments(root)
    assert "Papers" not in lab(root, "now")
    assert "papers:" not in lab(root, "check", "--no-rederive")


def test_a_paper_includes_only_finished_work_and_lists_each_id_once(tmp_path):
    root = str(tmp_path)
    first, void, later = two_experiments(root)
    papers(root)
    page(root, "entries/paper-a", included=(first, void, later), excluded=(first,), open_=("G1.Q9.1",))
    out = lab(root, "check", "--no-rederive", ok=False)
    assert f"lists {void} under included, which is void" in out and "list it under excluded" in out
    assert f"lists {later} under included, which is open" in out and "list it under open" in out
    assert f"lists {first} under both included and excluded" in out
    assert "lists G1.Q9.1 under open, which is not a goal, a question, a step or a decision of the lab" in out
    page(root, "entries/paper-a", included=(first,), excluded=(void,), open_=(first,))
    assert f"lists {first} under open, which is done" in lab(root, "check", "--no-rederive", ok=False)
    page(root, "entries/paper-a", included=(first, "D1"), excluded=(void,), open_=(later,))
    assert "the record is sound" in lab(root, "check", "--no-rederive")


def test_the_papers_table_names_pages_that_are_there_each_with_its_scope(tmp_path):
    root = str(tmp_path)
    two_experiments(root)
    papers(root, active=("entries/paper-a", "entries/paper-b", "entries/where-the-results-stand"))
    os.makedirs(f"{root}/docs/content/entries/paper-a", exist_ok=True)
    open(f"{root}/docs/content/entries/paper-a/index.html", "w").write("<html><body><td data-scope=\"kept\"></td></body></html>")
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "`active` names entries/paper-b, which is not a page of the library" in out
    assert "is the overview and an active paper" in out
    assert 'has no scope cell marked data-scope="included"' in out and 'marks a cell data-scope="kept"' in out
    papers(root, overview="entries/nowhere")
    assert "`overview` names entries/nowhere, which is not a page of the library" in lab(root, "check", "--no-rederive", ok=False)


def test_a_card_never_names_a_paper(tmp_path):
    root = str(tmp_path)
    first, _, _ = two_experiments(root)
    from test_flow import folder, front
    front(f"{folder(root, first)}/experiment.md", paper="paper-a")
    assert "`paper:` is not something a experiment card holds" in lab(root, "check", "--no-rederive", ok=False)


def test_now_puts_each_papers_open_row_first_and_names_what_serves_no_paper(tmp_path):
    root = str(tmp_path)
    first, void, later = two_experiments(root)
    papers(root)
    page(root, "entries/paper-a", included=(first,), excluded=(void,))
    now = lab(root, "now")
    assert "Paper A: The square-root law (entries/paper-a): open nothing" in now
    assert "Serving no active paper" in now and f"- {later} Error at 400 and at 1600 flips (open)" in now
    page(root, "entries/paper-a", included=(first,), excluded=(void,), open_=(later,))
    now = lab(root, "now")
    assert f"open {later} Error at 400 and at 1600 flips (open)" in now and "Serving no active paper" not in now
    page(root, "entries/paper-a", included=(first,), excluded=(void,), open_=("G1.Q1",))  # a question stands for every step under it
    assert "Serving no active paper" not in lab(root, "now")


def test_a_paper_older_than_a_result_it_lists_is_noted(tmp_path):
    root = str(tmp_path)
    first, void, later = two_experiments(root)
    papers(root)
    page(root, "entries/paper-a", included=(first,), excluded=(void,), open_=(later,))
    git_env(root, "init", "-q")
    git_env(root, "add", "-A")
    git_env(root, "commit", "-qm", "the paper", GIT_AUTHOR_DATE=PAST, GIT_COMMITTER_DATE=PAST)
    lab(root, "log", first, "result", "The error halves.", "It converges as the theory says.")
    commit(root, "the result")
    out = lab(root, "check", "--no-rederive", ok=False)  # the question's So far is stale too, which is a problem
    assert f"note: papers: entries/paper-a was last committed before the result of {first}" in out
    assert "papers:" not in out.split("note: papers:")[1].split("\n", 1)[1]  # a note, never a problem
