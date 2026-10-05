# Contributing

## Set up

```bash
python3 -m venv .venv
.venv/bin/pip install -e ../folio -e '.[dev]'
```

Use a checkout of folio beside this one, or `pip install folio-kb`.

## The gate

```bash
python -m pytest -q
(cd examples/monte-carlo-lab && lab-kit check)
```

The tests, then `lab-kit check` on the example lab. CI runs the same two commands.

## How a change lands

- The contract is `docs/spec/lab-model.md`. A change to a command or a check changes it in the same commit.
- Every lab check has a test that breaks a copy of the example lab and asserts the check's name.
- The method, the skills and the roles ship inside the package. A lab gets a new version of them from `lab-kit init`, never by hand.
- If the example lab changes, rebuild it with the commands it shows: `lab-kit lock`, `lab-kit run`, `lab-kit score`, and folio's commands for its documents. Its run evidence is never edited by hand.
- Write plain words in short sentences. Name no particular project, person or organisation in the docs or the code.
- Fail loud. A problem lab-kit cannot work around is an error with a message that says what to do.
