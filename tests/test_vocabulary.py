"""A word is defined once, in GLOSSARY.md: avoid and see on an entry, and a goal that lists names only."""
import glob, os
import re

import pytest

from test_flow import fill, front, lab, open_question
from test_integrity import commit, under

ENTRIES = ("# Words\n\n## guard\nThe part that reads every call and refuses the ones the contract forbids.\n- code: kna.gate:Guard\n- avoid: gate, filter, `policy`\n- see: entries/the-guard\n\n"
           "## field\nOne number on a grid.\n\n## LoRA\nA small adapter trained beside a frozen model.\n- see: notes:/content/concepts/lora/\n")


def a_lab(tmp_path, glossary=ENTRIES, vocabulary="- guard\n- field"):
    root = under(tmp_path, "lab")
    qdir = open_question(root)
    open(f"{root}/GLOSSARY.md", "w").write(glossary)
    goal = glob.glob(f"{root}/goals/G1-*/goal.md")[0]
    fill(goal, Vocabulary=vocabulary)
    os.makedirs(f"{root}/docs/content/entries/the-guard")
    open(f"{root}/docs/content/entries/the-guard/index.html", "w").write("<p>the guard</p>\n")
    os.makedirs(tmp_path / "notes" / "content" / "concepts" / "lora")
    open(tmp_path / "notes" / "content" / "concepts" / "lora" / "index.html", "w").write("<p>lora</p>\n")
    open(f"{root}/docs/folio.yaml", "w").write("title: lab\nlibraries:\n  notes:\n    path: ../../notes\n    url: https://notes.example\n")
    commit(root)
    return root, goal


def test_avoid_and_see_are_read_and_shown_and_a_sound_lab_checks(tmp_path):
    root, _ = a_lab(tmp_path)
    out = lab(root, "define", "guard")
    assert "guard: The part that reads every call" in out and "code: kna.gate:Guard" in out and "avoid: gate, filter, policy" in out and "see: entries/the-guard" in out
    assert "avoid:" not in lab(root, "define", "field") and "see: notes:/content/concepts/lora/" in lab(root, "define", "LoRA")
    assert "the record is sound" in lab(root, "check", "--strict")


def test_a_see_that_leads_nowhere_is_reported_like_a_cards(tmp_path):
    root, _ = a_lab(tmp_path)
    open(f"{root}/GLOSSARY.md", "a").write("\n## ghost\nNothing.\n- see: entries/not-there\n\n## stray\nNothing either.\n- see: elsewhere:/content/x/\n")
    out = lab(root, "check", ok=False)
    assert "GLOSSARY.md: ghost: see names the page entries/not-there, which is not in the library" in out
    assert "GLOSSARY.md: stray: see names elsewhere:/content/x/, which is not a page of a library the charter names" in out
    # the other library's page is missing while its folder is there
    os.remove(tmp_path / "notes" / "content" / "concepts" / "lora" / "index.html")
    os.rmdir(tmp_path / "notes" / "content" / "concepts" / "lora")
    assert "LoRA: see names notes:/content/concepts/lora/, and the library notes holds no such page" in lab(root, "check", ok=False)
    # the other library is not on the machine: a note, and a failure only when strict
    os.rename(tmp_path / "notes", tmp_path / "away")
    open(f"{root}/GLOSSARY.md", "w").write(ENTRIES)
    out = lab(root, "check")
    assert "the library notes is not here" in out and "the glossary name in it" in out and "problem(s)" not in out
    assert "not everything could be checked here" in lab(root, "check", "--strict", ok=False)


def test_the_glossary_page_shows_avoid_in_small_type_and_see_as_a_link_and_the_tooltip_is_the_definition(tmp_path):
    pytest.importorskip("folio.views")
    from lab_kit.site import Provider
    root, _ = a_lab(tmp_path)
    page = Provider(root).get("glossary").main
    assert '<span class="avoid">Avoid: gate, filter, policy</span>' in page
    assert 'See: <a href="/content/entries/the-guard/">' in page and 'href="https://notes.example/content/concepts/lora/"' in page
    goal = Provider(root).get("G1").main
    tip = re.search(r'<span class="term" data-tip="([^"]*)"', page + goal + Provider(root).get("G1.Q1").main)
    assert tip is None or "Avoid" not in tip.group(1)


def test_the_goal_lists_names_and_shows_the_glossarys_definitions(tmp_path):
    pytest.importorskip("folio.views")
    from lab_kit.site import Provider
    root, _ = a_lab(tmp_path)
    assert "the record is sound" in lab(root, "check", "--strict")
    main = Provider(root).get("G1").main
    assert "The words this lab uses" in main and "The part that reads every call and refuses the ones the contract forbids." in main and "One number on a grid." in main
    assert "Avoid: gate, filter, policy" in main
    shown = lab(root, "show", "G1")
    assert "- guard: The part that reads every call" in shown and "avoid: gate, filter, policy" in shown and "see: entries/the-guard" in shown and "- field: One number on a grid." in shown


def test_a_name_that_is_not_in_the_glossary_is_reported(tmp_path):
    pytest.importorskip("folio.views")
    from lab_kit.site import Provider
    root, _ = a_lab(tmp_path, vocabulary="- guard\n- sieve")
    out = lab(root, "check", ok=False)
    assert "Vocabulary lists 'sieve', which is not a term in GLOSSARY.md: add it there first" in out and "'guard'" not in out
    assert "- sieve: not in the glossary" in lab(root, "show", "G1")
    assert "not in the glossary" in Provider(root).get("G1").main


def test_the_old_form_is_reported_and_the_glossarys_text_is_shown_never_the_cards(tmp_path):
    pytest.importorskip("folio.views")
    from lab_kit.site import Provider
    root, _ = a_lab(tmp_path, vocabulary="- field: a number the card made up\n- sieve: another made-up meaning")
    out = lab(root, "check", ok=False)
    assert "Vocabulary lists 'field' with a meaning: list the name only, `- field`" in out
    assert "Vocabulary lists 'sieve', which is not a term in GLOSSARY.md" in out and "'sieve' with a meaning" not in out
    main, shown = Provider(root).get("G1").main, lab(root, "show", "G1")
    assert "One number on a grid." in main and "made up" not in main and "made-up" not in main
    assert "- field: One number on a grid." in shown and "made up" not in shown and "made-up" not in shown


def test_the_goal_a_new_lab_starts_with_has_an_empty_vocabulary_and_passes(tmp_path):
    root = under(tmp_path, "lab")
    open_question(root)
    assert "## Vocabulary" in open(glob.glob(f"{root}/goals/G1-*/goal.md")[0]).read()
    commit(root)
    assert "Vocabulary" not in lab(root, "check")


def test_markup_in_avoid_or_see_is_escaped(tmp_path):
    pytest.importorskip("folio.views")
    from lab_kit.site import Provider
    P = 'x"><script>alert(1)</script>'
    root, _ = a_lab(tmp_path, glossary=f"# Words\n\n## guard\nA guard.\n- avoid: {P}, <b>bold</b>\n- see: {P}\n\n## field\nA field.\n- see: other:{P}\n", vocabulary="- guard")
    for page in (Provider(root).get("glossary").main, Provider(root).get("G1").main):
        assert "<script>alert(1)" not in page and "<b>bold" not in page
    assert "&lt;script&gt;" in Provider(root).get("glossary").main
