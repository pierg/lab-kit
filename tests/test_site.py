"""The operator's site: every page drawn from the record for a reader, and every link on it landing somewhere."""
import glob
import json
import os
import re
import time

import pytest

if os.environ.get("LAB_SITE_TESTS") == "required":  # CI sets it once folio-kb 0.5.0 installs: from then on these never skip
    import folio.views  # noqa: F401
else:
    pytest.importorskip("folio.views")  # the views hook, in folio-kb 0.5.0 and later

from lab_kit.site import Provider  # noqa: E402
from html.parser import HTMLParser  # noqa: E402

from test_flow import describe, experiment, fill, front, lab, locked, results  # noqa: E402
from test_integrity import mutated  # noqa: E402
from test_needs import across  # noqa: E402


def a_lab(tmp_path):
    """One done experiment, a build, a second experiment held by an open decision, and a settled decision."""
    root, ident, d, command = locked(tmp_path)
    lab(root, "run", ident, "--wait", "--", *command)
    results(d, "0.5")
    lab(root, "review", ident, "results", "pass", "Re-ran it.")
    fill(f"{d}/experiment.md", Found="The error at 400 flips was {ratio} of the error at 100.", Means="It converges as the theory says.")
    qdir = os.path.dirname(d)
    fill(f"{qdir}/question.md", So_far="The error at 400 flips is {G1.Q1.1:ratio} of the error at 100.")
    lab(root, "new", "build", "G1.Q1", "A faster sampler")
    describe(glob.glob(f"{qdir}/2-*/build.md")[0], "The sampler rewritten to run on a GPU, for the larger sizes.")
    second, d2, command2 = experiment(root, title="Error at 1600 flips", uses="[gpu]")
    lab(root, "new", "decision", "A third size, on the GPU", "--about", second)
    card = glob.glob(f"{root}/decisions/D2-*.md")[0]
    fill(card, Seen="Two sizes confirm the law. A third would show whether it still holds further out.", Options="(a) Run 1600 flips on the GPU. (b) Stop at two sizes.", Recommendation="(a).")
    front(card, holds=f"[{second}]")
    lab(root, "log", "G1.Q1", "agent", "Chose two sizes, not three.", "A third adds nothing the theory does not give.")
    return root


def test_every_page_draws_and_every_link_lands(tmp_path):
    root = a_lab(tmp_path)
    site = Provider(root)
    paths = site.paths()
    assert {"", "graph", "decisions", "log", "resources", "glossary", "G1", "G1.Q1", "G1.Q1.1", "G1.Q1.2", "G1.Q1.3", "D1", "D2"} <= set(paths)
    seen = set()
    for path in paths:
        view = site.get(path)
        assert view is not None and view.title and "<h1>" not in view.main, path
        for href in re.findall(r'href="(/lab/[^"#?]*)', view.main + "".join(body for _, body in view.panels)):
            seen.add(href[len("/lab/"):].strip("/"))
    assert len(seen) > 8
    for inner in sorted(seen):
        assert site.get(inner) is not None, f"a page links to /lab/{inner}, which draws nothing"
    assert site.get("no/such/page") is None and site.get("log/nonsense") is None

    front_page = site.get("").main  # what there is to discuss is on the front page, complete, with what it holds
    assert all(x in front_page for x in ("To discuss with you", "A third size, on the GPU", "Two sizes confirm the law.", "(a) Run 1600 flips", "Held until it is settled", "Error at 1600 flips"))
    assert 'class="box decision"' in front_page and 'class="decisionq">A third size, on the GPU' in front_page
    assert 'class="decisionq">The lab' not in front_page  # a settled decision is no longer something to discuss
    assert "A coin estimate converges" in front_page and "The simplest check of the square-root law" not in front_page  # a goal in a line; a question that has a So far shows only that
    assert front_page.index("nobody is on it") < front_page.index("To discuss with you") < front_page.index("Where each question stands")  # the present first
    assert "The error at 400 flips is" in front_page and ">50%</a>" in front_page  # a named result reads the way its row says
    decided = site.get("decisions").main
    assert "One goal, convergence" in decided and "What came out of it" in site.get("D1").main and "Decided:" in site.get("log").main

    done = site.get("G1.Q1.1")
    assert done.status == "confirmed" and done.description == "" and '<p class="lead">Measures the error at two sample sizes, a factor of four apart.</p>' in done.main
    assert "Confirmed: every bar is met" in done.main and 'id="r-ratio"' in done.main and "the error at 400 flips as a share of the error at 100" in done.main
    assert "cat $RUN" not in done.main and 'data-tip="ratio &lt; 0.6"' in done.main and "<code>ratio" not in done.main  # no command and no test code for the reader
    assert "Ran 2 Jan" not in done.main and "Locked" in done.main and 'data-folio-copy="runs/' in done.main  # each run by its id, with its folder to copy
    waiting = site.get("G1.Q1.3")
    assert waiting.status == "waiting" and "not known yet" in waiting.main and "the decision" in waiting.main and "A third size, on the GPU" in waiting.main

    # every page of an entity names the file it is drawn from
    assert site.get("G1.Q1.1").path.endswith("/experiment.md") and site.get("G1.Q1.2").path.endswith("/build.md") and site.get("D1").path.startswith("decisions/D1-")
    assert site.get("glossary").path == "GLOSSARY.md" and site.get("resources").path == "resources.toml" and site.get("").path == ""
    assert all(os.path.exists(os.path.join(root, site.get(p).path)) for p in paths)


def test_a_failed_review_shows_no_outcome_and_what_is_replaced_or_dropped_is_folded(tmp_path):
    root, ident, d, command = locked(tmp_path)
    lab(root, "run", ident, "--wait", "--", *command)
    results(d, "0.5")
    lab(root, "review", ident, "results", "fail", "The seed was fixed after a first look.")
    site = Provider(root)
    page = site.get(ident)
    assert page.status == "review failed" and "failed their review" in page.main and "not known yet" in page.main and 'id="r-ratio"' not in page.main
    lab(root, "new", "experiment", "G1.Q1", "The same, with the seed fixed first", "--replaces", ident, "--because", "The seed was fixed after a first look at the numbers.")
    third, d3, _ = experiment(root, title="A size nobody needs")
    front(f"{d3}/experiment.md", dropped="The two sizes already answer it.")
    site = Provider(root)
    question = site.get("G1.Q1").main
    assert "The same, with the seed fixed first" in question and "second plan" in question and "Earlier plans, replaced" in question and "after a first look at the numbers" in question and question.count('<details class="row"') == 1
    assert "Dropped (1)" in question and "A size nobody needs" in question
    assert "Replaced by" in site.get(ident).main and site.get(ident).status == "replaced"
    assert [i["url"] for r in site.rail() if "items" in r for i in r["items"]] == ["/lab/G1.Q1.2/"]


def test_the_rail_the_search_and_the_stamp_follow_the_record(tmp_path):
    root, ident, d, command = locked(tmp_path)
    site = Provider(root)
    rail = site.rail()
    assert [r["title"] for r in rail[:6]] == ["Now", "Graph", "Decisions", "Log", "Resources", "Glossary"]
    question = next(r for r in rail if "items" in r)
    assert question["items"][0]["url"] == "/lab/G1.Q1.1/" and question["items"][0]["status"] == "planned" and question["tone"] == "info"
    assert any(s["url"] == "/lab/G1.Q1.1/" and "factor of four" in s["description"] for s in site.search()) and any(s["url"] == "/lab/D1/" for s in site.search())
    before = site.stamp()
    lab(root, "log", "G1.Q1.1", "stuck", "The machine is down.")
    assert site.stamp() != before and "The machine is down." in site.get("log").main


def test_the_front_page_says_what_the_agent_is_on_and_a_goal_tells_its_story(tmp_path):
    root = a_lab(tmp_path)
    fill(glob.glob(f"{root}/goals/G1-*/goal.md")[0], Claim="The sampler obeys the square-root law, against the textbook bound.")
    lab(root, "log", "G1.Q1.2", "doing", "Porting the sampler to the GPU.", "The third size needs it.")
    site = Provider(root)
    front_page = site.get("").main
    assert "the agent is on" in front_page and "Porting the sampler to the GPU." in front_page and "Why now:" in front_page and "Last recorded activity:" in front_page
    assert front_page.index("the agent is on") < front_page.index("To discuss with you") and "nobody is on it" not in front_page
    assert "Porting the sampler" not in site.get("G1.Q1").main and "Porting the sampler" in site.get("log/doing").main  # a doing line is the present, not history

    goal = site.get("G1").main
    assert "What we would claim, and against what" in goal and "against the textbook bound" in goal
    story = goal[goal.index("The story so far"):]
    assert story.index("A third size, on the GPU") < story.index("Chose two sizes, not three.") < story.index("One goal, convergence")  # the latest first: what is open, what was chosen, what was decided
    assert "decided with you" in story and "to discuss with you" in story and "Porting the sampler" not in story


def test_an_interval_reads_with_its_number_and_a_reviewers_note_is_never_linked(tmp_path):
    root, ident, d, command = locked(tmp_path)
    lab(root, "run", ident, "--wait", "--", *command)
    results(d, "0.5")
    with open(f"{d}/results.tsv", "a") as f:
        f.write("ratio.low\tlower end of its interval\t0.45\tpercent\tthe bar\tprintf 0.45\nratio.high\tupper end of its interval\t0.55\tpercent\tthe bar\tprintf 0.55\nspare\ta number no bar tests\t7\t\tnothing\tprintf 7\n")
    lab(root, "review", ident, "results", "pass", "The numbers are what the rows say. I re-ran every command against the run, and D1 fixed the bars before it started, and the thresholds are the ones G1.Q1 states, "
        "and nothing else was read, and the sampler was run twice more by me with other seeds, which gave the same ratio to two places both times.")
    fill(f"{d}/experiment.md", Found="The error at 400 flips was {ratio} of the error at 100.", Means="It converges as the theory says.")
    page = Provider(root).get(ident).main
    assert "50% (45% to 55%)" in page and 'id="r-ratio.high"' in page and "upper end of its interval" not in page  # the ends are shown with the number
    assert "1 more number this run gave, which no bar tests" in page and "a number no bar tests" in page
    note = page[page.index('<details class="note">'):]
    assert "<summary>The numbers are what the rows say.</summary>" in note and 'href="/lab/D1/"' not in note.split("</details>")[0]
    assert page.index("What it means") < page.index("What was found") < page.index("Confirmed: every bar is met")


def test_a_questions_page_is_its_briefing_and_a_bar_says_what_it_is_for(tmp_path):
    root = a_lab(tmp_path)
    third = glob.glob(f"{root}/goals/G1-*/Q1-*/3-*/experiment.md")[0]
    fill(third, Confirmed_if="- answer: the error at 1600 flips is under 0.3 of the error at 100 (`ratio < 0.3`)\n- readable: the sampler drew every estimate (`drawn >= 200`)",
         Outcomes="- **Under 0.3.** The law holds further out.\n- **Not all drawn.** Nothing is read.", Limits="- One seed.")
    front(third, cost='"Sixteen times the flips: two hours of the GPU."')
    site = Provider(root)
    page = site.get("G1.Q1.3").main
    assert page.index("The answer</th>") < page.index("The answer can be read only if</th>") < page.index("Would refute it</th>") and "answer:" not in page
    assert "What each outcome would mean" in page and "The law holds further out." in page and "What it cannot show" in page and "One seed." in page
    assert "Sixteen times the flips" in page and "up to 2 hours" in page and "plan/sample.py" in page
    q = site.get("G1.Q1").main
    order = ["What we know so far", "Why we ask", "What is needed from you", "The steps, and where each stands", "What it costs", "What it cannot show", "Where to look"]
    assert [q.index(x) for x in order] == sorted(q.index(x) for x in order) and "Sixteen times the flips" in q and "One seed." in q
    lab(root, "check", "--no-rederive")

    # a card links what the reader may not know; where nothing is drawn, the link is its words
    describe(third, "Follows [the square-root law](https://example.org/law), as the textbook states it.")
    site = Provider(root)
    assert '<a href="https://example.org/law">the square-root law</a>' in site.get("G1.Q1.3").main and "](https" not in site.get("G1.Q1.3").main
    assert "](https" not in site.get("graph").main and not any("](https" in s["description"] + s["text"] for s in site.search())
    assert "Follows the square-root law, as the textbook states it." in lab(root, "show", "G1.Q1.3")


def test_a_readings_page_says_it_is_exploratory_and_what_was_dropped_leaves_the_working_pages(tmp_path):
    root = a_lab(tmp_path)
    lab(root, "new", "reading", "G1.Q1", "Every estimate that missed, by cause")
    card = glob.glob(f"{root}/goals/G1-*/Q1-*/4-*/reading.md")[0]
    describe(card, "Reads the estimates that fell outside the band.")
    fill(card, Looks_at="Twelve estimates.", Seen="1. Nine used the short sample.\n2. Three had the seed reset.", Suggests="Fix the seed.")
    goal = glob.glob(f"{root}/goals/G1-*/goal.md")[0]
    fill(goal, Roles="- The sampler: our code. It draws every estimate.", Vocabulary="- tally: the card's own meaning, which is never shown", Approach="**The design.** Flip, count, compare.")
    open(f"{root}/GLOSSARY.md", "w").write("# Terms\n\n## tally\nOne share of heads, from one sample.\n")
    question = glob.glob(f"{root}/goals/G1-*/Q1-*/question.md")[0]
    fill(question, Example="1. **The sampler** flips a coin 100 times.\n2. **The scorer** compares the share of heads with one half.")
    lab(root, "new", "question", "G1", "A side question", "--from", "D1")
    front(glob.glob(f"{root}/goals/G1-*/Q2-*/question.md")[0], dropped='"Not this lab\'s to answer."')
    site = Provider(root)
    page = site.get("G1.Q1.4")
    assert page.status == "done" and "This looked at data the lab already had." in page.main and "<ol><li>Nine used the short sample.</li>" in page.main and "What it suggests" in page.main
    q = site.get("G1.Q1").main
    assert '<span class="kind">reading</span>' in q and "<ol><li><b>The sampler</b> flips a coin 100 times.</li>" in q and "Fix the seed." in q
    assert "The words this lab uses" in site.get("G1").main and "One share of heads, from one sample." in site.get("G1").main and "never shown" not in site.get("G1").main and "<b>The design.</b> Flip, count, compare." in site.get("G1").main
    assert "Who plays what" in site.get("G1").main and "It draws every estimate." in site.get("G1").main and "Dropped questions (1)" in site.get("G1").main
    assert "A side question" not in site.get("").main and not any("A side question" in str(r) for r in site.rail()) and site.get("G1.Q2") is not None


def test_an_experiments_page_lists_its_runs_in_order_with_what_changed(tmp_path):
    root, ident, d, command = locked(tmp_path)
    lab(root, "run", ident, "--wait", "--", *command, "not a number")  # the sampler stops on it; plan/ is as it was locked
    time.sleep(1.1)  # a run's start is recorded to the second
    open(f"{d}/plan/sample.py", "a").write("# reads its pause more carefully\n")
    lab(root, "run", ident, "--wait", "--changed", "The sampler exited at once; it now writes its ratio.", "--", *command)
    assert len(open(f"{d}/runs.tsv").read().splitlines()) == 5  # each run is listed when it starts and again, with its seal, when it ends
    page = Provider(root).get(ident).main
    import json
    first, second = (os.path.basename(d) for d in sorted(glob.glob(f"{root}/runs/*"), key=lambda d: json.load(open(f"{d}/run.json"))["started"]))
    assert re.fullmatch(r"\d{8}-\d{4}_G1\.Q1\.1_[a-z0-9]{4}", first)
    order = [f"<code>{first}</code>", "Stopped with an error", f'data-folio-copy="runs/{first}/"', f"<code>{second}</code>", "Changed since the run before", "The sampler exited at once", f'data-folio-copy="runs/{second}/"']
    assert [page.index(x) for x in order] == sorted(page.index(x) for x in order)
    assert "An experiment is run until one run finishes." in page


def every_page(root):
    """Every page of a lab's site, drawn: [(its path, its HTML)]. The rail, the search index and the backlinks are built too."""
    site = Provider(root)
    site.rail(), site.search(), site.backlinks()
    out = []
    for path in site.paths():
        view = site.get(path)
        out.append((path, view.main + "".join(block for _, block in view.panels)))
    return out


def test_every_page_draws_for_a_lab_that_is_not_written_as_the_model_says(tmp_path):
    for name, root, _ in mutated(tmp_path):
        try:
            every_page(root)
        except Exception as err:
            raise AssertionError(f"{name}: a page of the site does not draw: {err.__class__.__name__}: {err}") from err


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts, self.handlers, self.inside = [], [], False

    def handle_starttag(self, tag, attrs):
        self.inside = tag == "script"
        self.handlers += [(tag, k) for k, v in attrs if k.startswith("on") and "alert" in (v or "")]

    def handle_endtag(self, tag):
        self.inside = False

    def handle_data(self, data):
        if self.inside and "alert(1)" in data:
            self.scripts.append(data)


def test_nothing_written_in_a_lab_reaches_a_page_as_markup(tmp_path):
    P = 'x" onmouseover="alert(1)"><script>alert(1)</script>'
    Q = json.dumps(P)
    root = a_lab(tmp_path)
    open(f"{root}/lab.toml", "a").write(f"code_url = {json.dumps('https://example.com/' + P)}\n")
    open(f"{root}/GLOSSARY.md", "w").write(f"# {P}\n\n## sampler{P}\nWhat draws the estimates. {P}\n- code: {P}\n\n## estimate\nOne number from the sampler. {P}\n- code: sampler:{P}\n- avoid: {P}, <b>x</b>\n- see: {P}\n")
    open(f"{root}/resources.toml", "a").write(f"other_use = [{{date = \"2026-01-01\", amount = 1, what = {Q}}}]\n\n[{Q}]\nwhat = {Q}\nkey = {Q}\nunit = {Q}\ngranted = 5\nfrom = \"D1\"\nrules = [{Q}]\n")
    goal = glob.glob(f"{root}/goals/G1-*/goal.md")[0]
    qdir = glob.glob(f"{root}/goals/G1-*/Q1-*")[0]
    done, build, second = (glob.glob(f"{qdir}/{n}-*")[0] for n in (1, 2, 3))
    for card, slots in ((goal, ("Claim", "Example", "Approach")), (f"{qdir}/question.md", ("How_we_would_know", "Example", "We_expect", "Wrong_if")), (f"{build}/build.md", ("How_it_works", "Works_when")),
                        (f"{second}/experiment.md", ("Compares", "Cases", "Outcomes", "Limits")), (f"{done}/experiment.md", ("Means",))):
        fill(card, **{s: f"The sampler draws an estimate. {P} [a link]({P}) `{P}` **{P}** G1.Q1" for s in slots})
        describe(card, f"What it is and why. {P}")
        front(card, title=Q, see=f"[{Q}]")
    fill(goal, Roles=f"- {P}: {P}", Vocabulary=f"- {P}: {P}")
    front(f"{qdir}/question.md", asks=Q)
    fill(f"{second}/experiment.md", Arms=f"- {P}: {P}\n- other: {P}", Confirmed_if=f"- answer: {P} (`ratio < 0.6`)", Refuted_if=f"- {P} (`ratio > 0.9`)")
    front(f"{second}/experiment.md", cost=Q, waiting_on=Q)
    front(f"{build}/build.md", commits=f"[{Q}]", tests=f"[{Q}]")
    for d in glob.glob(f"{root}/decisions/D*.md"):
        fill(d, Seen=P, Options=f"- {P}\n- {P}", Recommendation=P)
        front(d, title=Q)
    rows = open(f"{done}/results.tsv").read().rstrip("\n").split("\t")
    rows[-5], rows[-2] = f"the share {P}", P  # its label, and what it is compared with
    os.chmod(f"{done}/results.tsv", 0o644)
    open(f"{done}/results.tsv", "w").write("\t".join(rows) + "\n")
    open(f"{done}/reviews.tsv", "a").write(f"2026-01-02\tresults\tpass\t{P}\tx\t{P}. And {P}\n")
    lab(root, "log", "G1.Q1", "agent", f"Chose {P}", f"Because {P}")
    lab(root, "log", "G1.Q1.3", "doing", f"Starting {P}", f"Because {P}")
    lab(root, "new", "reading", "G1.Q1", P)
    reading = glob.glob(f"{qdir}/4-*/reading.md")[0]
    describe(reading, P)
    fill(reading, Looks_at=P, Seen=f"- {P}", Suggests=P)
    lab(root, "new", "experiment", "G1.Q1", P, "--replaces", "G1.Q1.1", "--because", P)
    pages = every_page(root)
    assert len(pages) > 15
    for path, html_ in pages:
        tags = Tags()
        tags.feed(html_)
        assert not tags.scripts and not tags.handlers, f"/{path}: {tags.scripts[:1] or tags.handlers[:1]}"
        assert "alert(1)" in html_ or path in ("graph",) or path.startswith("log/"), f"/{path} shows none of what was written"  # the text is there, as text


def test_a_link_written_as_text_in_a_card_stays_text(tmp_path):
    root = a_lab(tmp_path)
    qdir = glob.glob(f"{root}/goals/G1-*/Q1-*")[0]
    fill(f"{qdir}/question.md", So_far='The page says href="/docs/notes" in so many words, and names G1.')
    page = Provider(root).get("G1.Q1").main
    assert 'says href="/docs/notes" in so many words' in page and 'href="/lab/G1/"' in page  # the prose as written, and the id still a link


def test_a_lost_run_stays_on_its_experiments_page_with_the_reason(tmp_path):
    root, ident, d, command = locked(tmp_path)
    gone = f"20260102-0931_{ident}_abcd"
    open(f"{d}/runs.tsv", "w").write("run\tkind\twhat\tat\texit\tseal\tused\tnote\n" + f"{gone}\trun\tstarted\t2026-01-02T09:31:00+00:00\t\t\n")
    page = Provider(root).get(ident).main
    assert f"<code>{gone}</code>" in page and "Still running." in page and "its folder is not in the store here" in page
    lab(root, "runs", "lost", gone, "The machine was deleted with the run on it.")
    page = Provider(root).get(ident).main
    assert f"<code>{gone}</code>" in page and "Stopped with an error: declared lost: The machine was deleted with the run on it." in page
    lab(root, "run", ident, "--wait", "--", *command)
    assert "Finished on its second run" in Provider(root).get(ident).main


def test_a_step_that_needs_a_later_one_reads_on_every_page_as_it_does_in_the_command(tmp_path):
    root = str(tmp_path)
    ident, d, later_card = across(root)  # a reading, a build and an experiment under Q1, each needing a done reading under Q2
    site = Provider(root)
    front_page = site.get("").main
    assert front_page.count("<td>the agent</td>") == 3 and "<td>waits</td>" not in front_page
    for step in ("G1.Q1.1", "G1.Q1.2", ident):
        assert "Next, for the agent:" in site.get(step).main and "Waiting on" not in site.get(step).main, step
    assert "Waiting on" not in site.get("G1.Q1").main and site.get("G1.Q1").main.count("Next: ") == 3
    assert [i["status"] for r in site.rail() if "items" in r for i in r["items"]] == ["planned", "planned", "planned", "done"]

    fill(later_card, Suggests="")  # the reading they need is not done: all three wait on it, on every page
    site = Provider(root)
    front_page = site.get("").main
    assert front_page.count("<td>waits</td>") == 3 and front_page.count("<td>the agent</td>") == 1
    for step in ("G1.Q1.1", "G1.Q1.2", ident):
        assert "Waiting on" in site.get(step).main and "Every estimate that missed, by cause" in site.get(step).main, step
    assert site.get("G1.Q1").main.count("Waiting on ") == 3
