"""The library's pages kept in step with the record: a lab that keeps `pages.toml` gives every page a kind, quotes a number
only as its card gives it, lands a storyline or stable page only on a page reviewer's pass, and records that each answer
reached its pages."""
import os

from test_flow import folder, front, lab
from test_storylines import storylines, two_experiments

SETTINGS = 'since = "2026-01-01"\ndropped = ["square-root law of everything"]\nnames = ["Model"]\n\n'


def pages_toml(root, kinds, settings=SETTINGS):
    open(f"{root}/docs/pages.toml", "w").write(settings + "[pages]\n" + "".join(f'"{p}" = "{k}"\n' for p, k in kinds.items()))


def write(root, path, body, tagged=False):
    d = os.path.join(root, "docs", "content", path)
    os.makedirs(d, exist_ok=True)
    meta = '<meta name="numbers" content="tagged">' if tagged else ""
    open(f"{d}/index.html", "w").write(f"<html><head><title>{path}</title>{meta}</head><body><main>{body}</main></body></html>")


def glossary(root, definition="The error at the larger sample as a share of the error at the smaller one."):
    open(f"{root}/GLOSSARY.md", "w").write(f"# Terms\n\n## error ratio\n\n{definition}\n- also: ratio\n")


def a_lab(root):
    first, void, later = two_experiments(root)  # G1.Q1.1 done (ratio 0.5, read as a percent), G1.Q1.2 void, G1.Q1.3 open
    glossary(root)
    write(root, "entries/the-error-halves", f'<p>The error fell to <span data-result="{first}:ratio">50%</span> of itself.</p>', tagged=True)
    write(root, "entries/what-a-ratio-is", "<p>A ratio compares two errors.</p>")
    pages_toml(root, {"entries/the-error-halves": "storyline", "entries/what-a-ratio-is": "stable", "entries/where-the-results-stand": "reference"})
    return first, void, later


def test_a_lab_without_pages_toml_is_unchanged(tmp_path):
    root = str(tmp_path)
    two_experiments(root)
    assert "pages:" not in lab(root, "check", "--no-rederive")
    assert "Pages" not in lab(root, "now")
    assert "keeps no pages.toml" in lab(root, "pages", ok=False)


def test_every_page_has_a_kind_and_pages_toml_says_what_it_holds(tmp_path):
    root = str(tmp_path)
    a_lab(root)
    write(root, "concepts/sample", "<p>Flips.</p>")
    pages_toml(root, {"entries/the-error-halves": "storyline", "entries/what-a-ratio-is": "chapter", "entries/gone": "reference"},
               settings='colour = "blue"\n')
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "concepts/sample has no kind" in out and "entries/where-the-results-stand has no kind" in out
    assert "gives entries/what-a-ratio-is the kind 'chapter'" in out
    assert "lists entries/gone, which is not a page of the library" in out
    assert "holds `colour`" in out and "names no `since" in out
    assert "docs/pages.toml" in lab(root, "pages", "passed", "entries/the-error-halves", "Read it.", ok=False)


def test_a_quoted_number_is_the_cards_and_its_results_were_reviewed(tmp_path):
    root = str(tmp_path)
    first, void, _ = a_lab(root)
    for page in ("entries/the-error-halves", "entries/what-a-ratio-is"):
        lab(root, "pages", "passed", page, "Every number matches its card.")
    assert "the record is sound" in lab(root, "check", "--no-rederive")
    cases = {
        f'<span data-result="{first}:ratio">60%</span>': "shows 60 for G1.Q1.1:ratio, but the card says 50",
        f'<span data-result="{first}:ratio">50.0%</span> and <span data-result="{first}:ratio">49.96</span>': "shows 49.96",
        f'<span data-result="{first}:flips">400</span>': "G1.Q1.1 has no result 'flips'",
        f'<span data-result="{void}:ratio">25%</span>': "the results of G1.Q1.2 are not reviewed",
        '<span data-result="G1.Q7.1:ratio">5</span>': "names no result of an experiment of the record",
        f'<span data-result="{first}:ratio">half</span>': "shows no number",
        f'<span data-result="{first}:ratio">50%</span> over 200 estimates': "shows numbers outside a data-result element (200)",
    }
    for body, said in cases.items():
        write(root, "entries/the-error-halves", body, tagged=True)
        assert said in lab(root, "check", "--no-rederive", ok=False), body
    # a count of what is studied, a total, a year and a number after a name the lab lists are not results
    write(root, "entries/the-error-halves", f'<p><span data-result="{first}:ratio">50</span> of 100, in 2026, on Model 4, '
          f'<span data-plain>200</span> estimates, <code>n = 400</code>.</p>', tagged=True)
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "outside a data-result" not in out and "no page reviewer has passed it" in out


def test_a_storyline_or_stable_page_lands_only_on_a_reviewers_pass_and_is_read_again_only_when_it_changes(tmp_path):
    root = str(tmp_path)
    a_lab(root)
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "entries/the-error-halves: no page reviewer has passed it" in out and "entries/what-a-ratio-is: no page reviewer" in out
    assert "where-the-results-stand: no page reviewer" not in out  # a reference page is not held
    assert "waits for a page reviewer" in lab(root, "now")
    assert "one line" in lab(root, "pages", "passed", "entries/what-a-ratio-is", 'Read "all" of it.', ok=False)
    assert "has no kind" in lab(root, "pages", "passed", "entries/elsewhere", "Read it.", ok=False)
    lab(root, "pages", "passed", "entries/the-error-halves", "The number matches G1.Q1.1.")
    lab(root, "pages", "passed", "entries/what-a-ratio-is", "Reads cold.")
    assert "the record is sound" in lab(root, "check", "--no-rederive")
    listing = lab(root, "pages")
    assert "entries/the-error-halves: passed" in listing and "entries/where-the-results-stand: never read" in listing
    write(root, "entries/what-a-ratio-is", "<p>A ratio compares two errors, the larger sample's over the smaller's.</p>")
    assert "entries/what-a-ratio-is: no page reviewer has passed it" in lab(root, "check", "--no-rederive", ok=False)
    write(root, "entries/what-a-ratio-is", "<p>A ratio compares two errors.</p>")  # back as it was passed: nothing to read again
    assert "the record is sound" in lab(root, "check", "--no-rederive")


def test_a_term_links_to_its_one_definition_whose_hover_text_follows_the_glossary(tmp_path):
    root = str(tmp_path)
    a_lab(root)
    write(root, "entries/what-a-ratio-is", '<p>An <a class="term" href="/lab/glossary/#error-ratio">error ratio</a> and a '
          '<a class="term" href="/lab/glossary/#ratio">ratio</a> and a <a class="term" href="/lab/glossary/#flip">flip</a>.</p>')
    lab(root, "pages", "passed", "entries/the-error-halves", "Checked.")
    lab(root, "pages", "passed", "entries/what-a-ratio-is", "Checked.")
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "links the glossary term 'flip', which GLOSSARY.md has no entry for" in out
    assert "the hover text of the link to 'error-ratio' is not its glossary definition: run `lab pages terms`" in out
    assert "hover text written in docs/content/entries/what-a-ratio-is/index.html" in lab(root, "pages", "terms")
    text = open(f"{root}/docs/content/entries/what-a-ratio-is/index.html").read()
    assert text.count('title="The error at the larger sample as a share of the error at the smaller one."') == 2
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "hover text" not in out and "no page reviewer" not in out  # the hover text is not part of what a reviewer passed
    glossary(root, "The larger sample's error over the smaller's.")
    assert "is not its glossary definition" in lab(root, "check", "--no-rederive", ok=False)
    lab(root, "pages", "terms")
    assert "'flip'" in lab(root, "check", "--no-rederive", ok=False)


def test_no_page_but_a_retiring_one_uses_a_dropped_phrase_or_claims_to_be_first(tmp_path):
    root = str(tmp_path)
    a_lab(root)
    write(root, "entries/where-the-results-stand", "<p>This is the Square-root law of everything. We show for the first time that it holds.</p>"
          "<p>To our knowledge, the first proofs of it are ours.</p>")
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "says 'Square-root law of everything', a phrase docs/pages.toml drops" in out
    assert "claims to be first ('for the first time')" in out and "the first proofs" not in out
    pages_toml(root, {"entries/the-error-halves": "storyline", "entries/what-a-ratio-is": "stable", "entries/where-the-results-stand": "retiring"})
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "a phrase docs/pages.toml drops" not in out and "claims to be first" not in out


def test_an_answer_reaches_its_pages_before_the_record_is_sound(tmp_path):
    root = str(tmp_path)
    first, _, later = a_lab(root)
    lab(root, "pages", "passed", "entries/the-error-halves", "Checked.")
    lab(root, "pages", "passed", "entries/what-a-ratio-is", "Checked.")
    assert lab(root, "pages", "cites", "G1.Q1").strip() == "entries/the-error-halves"
    assert "no storyline page cites G1.Q2" in lab(root, "pages", "cites", "G1.Q2")
    assert "not an answered question" in lab(root, "pages", "answered", "G1.Q1", "Revised.", ok=False)
    front(f"{folder(root, later)}/experiment.md", dropped='"Not needed once the first experiment answered it."')
    assert "lab pages cites G1.Q1" in lab(root, "answer", "G1.Q1", "yes", "The error halves when the sample quadruples.")
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "G1.Q1: answered 2026-01-02, and no row of answers-in-pages.tsv says its answer reached its pages" in out
    assert "G1.Q1 answered 2026-01-02: its pages are not revised yet" in lab(root, "now")
    write(root, "entries/the-error-halves", f'<p>The error halves: <span data-result="{first}:ratio">50%</span>.</p>', tagged=True)
    assert "wait for a page reviewer's pass first: entries/the-error-halves" in lab(root, "pages", "answered", "G1.Q1", "Revised.", ok=False)
    lab(root, "pages", "passed", "entries/the-error-halves", "The answer matches its card.")
    lab(root, "pages", "answered", "G1.Q1", "entries/the-error-halves")
    assert "already recorded" in lab(root, "pages", "answered", "G1.Q1", "Again.", ok=False)
    assert "the record is sound" in lab(root, "check", "--no-rederive")
    assert "Pages" not in lab(root, "now")
    # an answer before `since` is not held
    pages_toml(root, {"entries/the-error-halves": "storyline", "entries/what-a-ratio-is": "stable", "entries/where-the-results-stand": "reference"},
               settings='since = "2026-02-01"\n')
    os.remove(f"{root}/docs/answers-in-pages.tsv")
    assert "the record is sound" in lab(root, "check", "--no-rederive")


def test_the_scope_page_links_every_storyline_page(tmp_path):
    root = str(tmp_path)
    first, void, later = a_lab(root)
    storylines(root, active=("entries/storyline-a",))
    from test_storylines import page
    page(root, "entries/storyline-a", included=(first,), excluded=(void,), open_=(later,))
    pages_toml(root, {"entries/the-error-halves": "storyline", "entries/what-a-ratio-is": "stable", "entries/where-the-results-stand": "reference",
                      "entries/storyline-a": "reference"})
    assert "the scope page does not link the storyline page entries/the-error-halves" in lab(root, "check", "--no-rederive", ok=False)
    text = open(f"{root}/docs/content/entries/storyline-a/index.html").read()
    open(f"{root}/docs/content/entries/storyline-a/index.html", "w").write(text.replace("</main>", '<a href="/content/entries/the-error-halves/">The error halves</a></main>'))
    assert "does not link the storyline page" not in lab(root, "check", "--no-rederive", ok=False)


def test_what_pages_toml_may_hold_and_what_it_turns_off(tmp_path):
    root = str(tmp_path)
    a_lab(root)
    for settings, said in {
        'since = "2026-13-45"\n': "`since` is '2026-13-45', not a date",
        'since = 2026-01-01\ndropped = ["(unclosed"]\n': "`dropped` holds '(unclosed', which is not a regular expression",
        'since = 2026-01-01\nnames = "Model"\n': "`names` lists words",
        'since = 2026-01-01\nsections = ["entries/deep"]\n': "`sections` lists the folders under content/",
        'since = 2026-01-01\nfirst = true\n': "`first` lists phrases",
    }.items():
        pages_toml(root, {"entries/the-error-halves": "storyline"}, settings=settings)
        assert said in lab(root, "check", "--no-rederive", ok=False), settings
        assert "needs fixing before the pages can be checked" in lab(root, "now")
    pages_toml(root, {"../outside": "reference"})
    assert "lists ../outside; a page is a path inside the library's content" in lab(root, "check", "--no-rederive", ok=False)
    # only the sections listed need a kind; `first = []` turns the claim check off, and a lab may name its own claims
    write(root, "notes/a-note", "<p>We show for the first time that it halves.</p><p>It is a breakthrough.</p>")
    kinds = {"entries/the-error-halves": "storyline", "entries/what-a-ratio-is": "stable", "entries/where-the-results-stand": "reference"}
    pages_toml(root, kinds, settings='since = 2026-01-01\nsections = ["notes"]\nfirst = []\n')
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "notes/a-note has no kind" in out and "entries/where-the-results-stand has no kind" not in out and "claims to be first" not in out
    pages_toml(root, {**kinds, "notes/a-note": "reference"}, settings='since = 2026-01-01\nsections = ["notes"]\nfirst = ["breakthrough"]\n')
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "claims to be first ('breakthrough')" in out and "'for the first time'" not in out


def test_results_are_quoted_as_the_card_shows_them_and_only_while_they_stand(tmp_path):
    root = str(tmp_path)
    first, void, _ = a_lab(root)
    lab(root, "pages", "passed", "entries/what-a-ratio-is", "Checked.")
    for body, said in {
        f'<span data-result="{first}:ratio+ratio">1</span>': "adds a percentage or a difference in points to other results",
        f'<span data-result="{first}:ratio">50%</span>': None,
        f'<table><tr><td data-result="{first}:ratio">50%<td>of the error</table>': None,  # an end tag HTML leaves out
        '<p>The error halves.</p>': None,
    }.items():
        write(root, "entries/the-error-halves", body, tagged=True)
        lab(root, "pages", "passed", "entries/the-error-halves", "Checked.")
        out = lab(root, "pages", "check", ok=said is None)
        assert (said in out) if said else out.strip() == "the pages are in step with the record", body
    open(f"{root}/docs/content/entries/the-error-halves/index.html", "w").write(
        f'<meta name="numbers" content="tagged"><p><span data-result="{first}:ratio">50%')
    assert "is still open where the page ends" in lab(root, "pages", "check", ok=False)
    write(root, "entries/the-error-halves", "<p>The error halves.</p>")
    assert "is a storyline page without `<meta name=\"numbers\" content=\"tagged\">`" in lab(root, "pages", "check", ok=False)
    write(root, "entries/the-error-halves", f'<span data-result="{first}:ratio">50%</span>', tagged=True)
    front(f"{folder(root, first)}/experiment.md", dropped='"A sampler bug was found after it ran."')
    assert f"the results of {first} are not reviewed, or {first} was replaced or dropped" in lab(root, "pages", "check", ok=False)
    pages_toml(root, {"entries/the-error-halves": "storyline", "entries/gone": "reference"})
    assert "has no HTML file" in lab(root, "pages", "passed", "entries/gone", "Checked.", ok=False)


def test_a_share_is_quoted_as_the_card_rounds_it_or_half_up(tmp_path):
    from test_flow import experiment, open_question
    from test_integrity import WRITES, done
    root = str(tmp_path)
    open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.0125")
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    done(root, ident, d, value="0.0125")
    os.makedirs(f"{root}/docs", exist_ok=True)
    pages_toml(root, {"entries/a-share": "reference"})
    for shown, ok in (("1.2%", True), ("1.3%", True), ("1%", True), ("1.4%", False), ("0.0125", False)):
        write(root, "entries/a-share", f'<span data-result="{ident}:ratio">{shown}</span>')
        out = lab(root, "pages", "check", ok=ok)
        assert ok or "but the card says" in out, shown
