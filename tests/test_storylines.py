"""Storylines drive the work: the record names no storyline, and each active storyline's page opens with a scope table whose
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


def page(root, path, title="Storyline A: The square-root law", included=(), excluded=(), open_=()):
    d = os.path.join(root, "docs", "content", path)
    os.makedirs(d, exist_ok=True)
    open(f"{d}/index.html", "w").write(PAGE.format(title=title, included=links(*included), excluded=links(*excluded), open=links(*open_)))


def storylines(root, overview="entries/where-the-results-stand", active=("entries/storyline-a",), listed=None):
    text = open(f"{root}/lab.toml").read().split("[storylines]")[0]
    open(f"{root}/lab.toml", "w").write(text + f'[storylines]\noverview = "{overview}"\nactive = [{", ".join(chr(34) + a + chr(34) for a in active)}]\n')
    home_map(root, active if listed is None else listed)


def home_map(root, listed, name="library"):
    os.makedirs(f"{root}/docs/content/maps", exist_ok=True)
    rows = "".join(f'<li><a href="/content/{a}/">{a}</a></li>' for a in listed)
    open(f"{root}/docs/content/maps/{name}.html", "w").write(
        f'<html><body><main><h2 id="current-storylines">Current storylines</h2><ul class="rows">{rows}</ul>'
        f'<h2 id="what-the-lab-proves">What the lab proves</h2><ul class="rows"><li><a href="/content/entries/where-the-results-stand/">Overview</a></li></ul></main></body></html>')


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


def test_a_lab_without_storylines_is_unchanged(tmp_path):
    root = str(tmp_path)
    two_experiments(root)
    assert "Storylines" not in lab(root, "now")
    assert "storylines:" not in lab(root, "check", "--no-rederive")


def test_a_storyline_includes_only_finished_work_and_lists_each_id_once(tmp_path):
    root = str(tmp_path)
    first, void, later = two_experiments(root)
    storylines(root)
    page(root, "entries/storyline-a", included=(first, void, later), excluded=(first,), open_=("G1.Q9.1",))
    out = lab(root, "check", "--no-rederive", ok=False)
    assert f"lists {void} under included, which is void" in out and "list it under excluded" in out
    assert f"lists {later} under included, which is open" in out and "list it under open" in out
    assert f"lists {first} under both included and excluded" in out
    assert "lists G1.Q9.1 under open, which is not a goal, a question, a step or a decision of the lab" in out
    page(root, "entries/storyline-a", included=(first,), excluded=(void,), open_=(first,))
    assert f"lists {first} under open, which is done" in lab(root, "check", "--no-rederive", ok=False)
    page(root, "entries/storyline-a", included=(first, "D1"), excluded=(void,), open_=(later,))
    assert "the record is sound" in lab(root, "check", "--no-rederive")


def test_the_storylines_table_names_pages_that_are_there_each_with_its_scope(tmp_path):
    root = str(tmp_path)
    two_experiments(root)
    storylines(root, active=("entries/storyline-a", "entries/storyline-b", "entries/where-the-results-stand"))
    os.makedirs(f"{root}/docs/content/entries/storyline-a", exist_ok=True)
    open(f"{root}/docs/content/entries/storyline-a/index.html", "w").write("<html><body><td data-scope=\"kept\"></td></body></html>")
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "`active` names entries/storyline-b, which is not a page of the library" in out
    assert "is the overview and an active storyline" in out
    assert 'has no scope cell marked data-scope="included"' in out and 'marks a cell data-scope="kept"' in out
    storylines(root, overview="entries/nowhere")
    assert "`overview` names entries/nowhere, which is not a page of the library" in lab(root, "check", "--no-rederive", ok=False)


def test_a_card_never_names_a_storyline(tmp_path):
    root = str(tmp_path)
    first, _, _ = two_experiments(root)
    from test_flow import folder, front
    front(f"{folder(root, first)}/experiment.md", storyline="storyline-a")
    assert "`storyline:` is not something a experiment card holds" in lab(root, "check", "--no-rederive", ok=False)


def test_now_puts_each_storylines_open_row_first_and_names_what_serves_no_storyline(tmp_path):
    root = str(tmp_path)
    first, void, later = two_experiments(root)
    storylines(root)
    page(root, "entries/storyline-a", included=(first,), excluded=(void,))
    now = lab(root, "now")
    assert "Storyline A: The square-root law (entries/storyline-a): open nothing" in now
    assert "Serving no active storyline" in now and f"- {later} Error at 400 and at 1600 flips (open)" in now
    page(root, "entries/storyline-a", included=(first,), excluded=(void,), open_=(later,))
    now = lab(root, "now")
    assert f"open {later} Error at 400 and at 1600 flips (open)" in now and "Serving no active storyline" not in now
    page(root, "entries/storyline-a", included=(first,), excluded=(void,), open_=("G1.Q1",))  # a question stands for every step under it
    assert "Serving no active storyline" not in lab(root, "now")


def test_a_storyline_older_than_a_result_it_lists_is_noted(tmp_path):
    root = str(tmp_path)
    first, void, later = two_experiments(root)
    storylines(root)
    page(root, "entries/storyline-a", included=(first,), excluded=(void,), open_=(later,))
    git_env(root, "init", "-q")
    git_env(root, "add", "-A")
    git_env(root, "commit", "-qm", "the storyline", GIT_AUTHOR_DATE=PAST, GIT_COMMITTER_DATE=PAST)
    lab(root, "log", first, "result", "The error halves.", "It converges as the theory says.")
    commit(root, "the result")
    out = lab(root, "check", "--no-rederive", ok=False)  # the question's So far is stale too, which is a problem
    assert f"note: storylines: entries/storyline-a was last committed before the result of {first}" in out
    assert "storylines:" not in out.split("note: storylines:")[1].split("\n", 1)[1]  # a note, never a problem


def test_every_rule_on_a_row_and_on_the_table_has_a_refusal(tmp_path):
    root = str(tmp_path)
    first, void, later = two_experiments(root)
    storylines(root)
    from test_flow import folder, front
    front(f"{folder(root, later)}/experiment.md", dropped="the first comparison answers the question")
    lab(root, "answer", "G1.Q1", "yes", "It halves at 400 flips.")
    page(root, "entries/storyline-a", included=(first,), excluded=(void,), open_=("G1.Q1",))
    assert "lists G1.Q1 under open, which is done" in lab(root, "check", "--no-rederive", ok=False)
    page(root, "entries/storyline-a", included=("G1", first), excluded=(void,), open_=("G1",))
    assert "lists G1 under both included and open" in lab(root, "check", "--no-rederive", ok=False)
    # a question written in one row and a step under it in another is allowed
    page(root, "entries/storyline-a", included=("G1.Q1",), excluded=(void, later), open_=())
    assert "storylines:" not in lab(root, "check", "--no-rederive")
    page(root, "entries/storyline-a", included=(first,), excluded=("G1.Q1", void), open_=())
    assert "storylines:" not in lab(root, "check", "--no-rederive")
    for table, said in (('storylines = "entries/storyline-a"', "`[storylines]` is a table"),
                        ('[storylines]\noverview = "entries/where-the-results-stand"\nkept = 1', "`[storylines]` holds `kept`"),
                        ('[storylines]\noverview = 3', "`[storylines]` names its `overview`"),
                        ('[storylines]\noverview = "entries/where-the-results-stand"\nactive = "entries/storyline-a"', "lists its `active` storyline pages"),
                        ('[storylines]\noverview = "entries/where-the-results-stand"\nactive = ["entries/storyline-a", "entries/storyline-a/"]', "lists entries/storyline-a more than once"),
                        ('[storylines]\noverview = "../outside"', "without `..`")):
        text = open(f"{root}/lab.toml").read().split("[storylines]")[0].split("storylines =")[0]
        open(f"{root}/lab.toml", "w").write(text + table + "\n")
        assert said in lab(root, "check", "--no-rederive", ok=False), table


def test_a_parked_or_dropped_question_is_in_neither_included_nor_open(tmp_path):
    root = str(tmp_path)
    first, void, later = two_experiments(root)
    from test_parked import park
    card, d = park(root, "G1.Q1", "Set the first sizes aside", "")
    lab(root, "decide", d, "--with", "Ada", "Set the first sizes aside until the sampler is fixed.")
    storylines(root)
    page(root, "entries/storyline-a", included=("G1.Q1",), excluded=(void,))
    assert "lists G1.Q1 under included, which is parked" in lab(root, "check", "--no-rederive", ok=False)
    page(root, "entries/storyline-a", excluded=(void,), open_=("G1.Q1",))
    assert "lists G1.Q1 under open, which is parked" in lab(root, "check", "--no-rederive", ok=False)


def test_a_cell_left_open_ends_where_the_next_cell_begins(tmp_path):
    root = str(tmp_path)
    first, void, later = two_experiments(root)
    storylines(root)
    d = f"{root}/docs/content/entries/storyline-a"
    os.makedirs(d, exist_ok=True)
    open(f"{d}/index.html", "w").write(f'<html><head><title>Storyline A</title></head><body><table><tr><td data-scope="included">{links(first)}'
                                       f'<tr><td data-scope="excluded">{links(void)}<tr><td data-scope="open">{links(later)}</table></body></html>')
    assert "storylines:" not in lab(root, "check", "--no-rederive")
    assert f"open {later} Error at 400 and at 1600 flips (open)" in lab(root, "now")


def test_a_table_inside_a_scope_cell_is_read_as_part_of_it(tmp_path):
    root = str(tmp_path)
    first, void, later = two_experiments(root)
    storylines(root)
    d = f"{root}/docs/content/entries/storyline-a"
    os.makedirs(d, exist_ok=True)
    open(f"{d}/index.html", "w").write(f'<html><body><table><tr><td data-scope="included"><table><tr><td>{links(first, void)}</td></tr></table></td>'
                                       f'<td data-scope="excluded"></td><td data-scope="open">{links(later)}</td></tr></table></body></html>')
    assert f"lists {void} under included, which is void" in lab(root, "check", "--no-rederive", ok=False)


def test_the_home_map_lists_the_active_storylines_under_current_storylines(tmp_path):
    root = str(tmp_path)
    first, void, later = two_experiments(root)
    page(root, "entries/storyline-a", included=(first,), excluded=(void,), open_=(later,))
    page(root, "entries/storyline-b", included=(first,), excluded=(void,), open_=(later,))
    storylines(root, active=("entries/storyline-a", "entries/storyline-b"), listed=("entries/storyline-a", "entries/old-storyline"))
    out = lab(root, "check", "--no-rederive", ok=False)
    assert '"Current storylines" has no row for entries/storyline-b' in out
    assert '"Current storylines" lists entries/old-storyline, which is not an active storyline' in out
    home_map(root, ("entries/storyline-a",), name="another")
    assert 'has a second "Current storylines" section' in lab(root, "check", "--no-rederive", ok=False)
    os.remove(f"{root}/docs/content/maps/another.html")
    os.remove(f"{root}/docs/content/maps/library.html")
    assert 'no map of the library has a section `<h2 id="current-storylines">' in lab(root, "check", "--no-rederive", ok=False)
    home_map(root, ("entries/storyline-a", "entries/storyline-b"))
    assert "storylines:" not in lab(root, "check", "--no-rederive")
