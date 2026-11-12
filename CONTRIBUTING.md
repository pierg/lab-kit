# Contributing

## Set up

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev,site]'
```

Python 3.10 or later. The `site` extra brings folio (`folio-kb` 0.5.0 or later), which only the
site's tests need; with a checkout of folio beside this one, `pip install -e ../folio` instead.
Without folio, `tests/test_site.py` skips itself and the rest runs; CI sets `LAB_SITE_TESTS=required`,
so there it never skips.

## The gate

```bash
python -m pytest -q
```

The tests build a small lab with the `lab` command itself and take it from a decision to a reviewed
result. CI runs them on Python 3.10 and 3.12, then builds the wheel, installs it alone and runs
`lab init` and `lab check` in an empty folder.

## How a change lands

- The contract is `docs/model.md`. Change it first, then the code, the method and the skills, in the
  same change.
- A rule a command holds is in `docs/model.md`, in the code and in a test together, and the test has
  a case that the command refuses.
- A command validates before it writes, and says what it wrote. No command writes a computed view
  into a lab.
- The method, the skills and the reviewer role ship inside the package. A lab gets a new version of
  them from `lab init`, never by hand, and `lab check` fails while they differ.
- Write plain words in short sentences. Name no particular project, person or organisation in the
  docs or the code.
- Fail loud. A problem lab-kit cannot work around is an error with a message that says what to do.
