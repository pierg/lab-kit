"""Read a lab's record as a tree: goals, questions, experiments and builds, runs, results, and the decisions that shaped it.

Nothing here writes. Every state is worked out from what the files hold: a card carries no status.
"""
from __future__ import annotations

import datetime, glob, hashlib, json, math, os, re

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10: the same parser, from PyPI
    import tomli as tomllib

import yaml

KINDS = ["decision", "agent", "result", "stuck", "doing"]  # a decision recorded, a choice of the agent's, a result, something in the way, what the agent is on now
CLOSES = ("agent", "result", "stuck")  # a later line of these kinds about the same card ends a `doing` line
SLOTS = {  # every slot a card has, with its word budget
    "goal": (("Claim", 90), ("Example", 260), ("Approach", 340), ("Roles", 170), ("Vocabulary", 260)),
    "question": (("How we would know", 150), ("Example", 380), ("We expect", 70), ("Wrong if", 70), ("So far", 120)),
    "experiment": (("Compares", 80), ("Arms", 260), ("Cases", 100), ("Confirmed if", 150), ("Refuted if", 110), ("Outcomes", 200), ("Limits", 120), ("Found", 130), ("Means", 90)),
    "build": (("How it works", 200), ("Works when", 80)),
    "reading": (("Looks at", 110), ("Seen", 320), ("Suggests", 150)),
    "decision": (("Seen", 120), ("Options", 200), ("Recommendation", 80)),
}
# What a reader who was not there needs under every title. A question's is its motivation, so it gets room.
DESCRIPTION = {"goal": 70, "question": 130, "experiment": 70, "build": 60, "reading": 70}
STEPS = ("experiment", "build", "reading")  # what sits under a question: a locked comparison, something made, a look at what already exists
READS = ("", "percent", "points")  # how a result's value reads on a page
BEFORE = ("Compares", "Arms", "Cases", "Confirmed if", "Refuted if", "Outcomes", "Limits")  # what an experiment says before it runs, and what its lock holds
ROLES = {"answer": "The answer", "readable": "The answer can be read only if", "counts": "The answer counts only if"}  # what a confirmed-if bar is there for
LINE = re.compile(r"^(?:(?P<role>answer|readable|counts):\s*)?(?P<say>.+?)\s*\(`(?P<name>[A-Za-z][\w.-]*)\s*(?P<op><=|>=|<|>)\s*(?P<num>-?\d+(?:\.\d+)?)`\)$")
NAMED = re.compile(r"\{(?:(G\d+\.Q\d+\.\d+):)?([A-Za-z][\w.-]*?)\}")  # a result named on a card: {name}, or {G1.Q1.2:name} from elsewhere
OPS = {"<": lambda a, b: a < b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, ">=": lambda a, b: a >= b}
OPPOSITE = {"<": ">=", ">=": "<", "<=": ">", ">": "<="}
CLOCK = re.compile(r"^\d\d:\d\d$")
DAY = re.compile(r"^\d{4}-\d\d-\d\d$")
RUN_ID = re.compile(r"^\d{8}-\d{4}_G\d+\.Q\d+\.\d+_[a-z0-9]{4}$")  # <date>-<time>_<experiment>_<four characters>
# runs.tsv, beside the lock: one row when a run starts, one when it ends (its exit and its seal), or one that declares
# it lost (what it used, and why). A file written before `used` and `note` existed has the first six columns.
LEDGER = ("run", "kind", "what", "at", "exit", "seal", "used", "note")
COLUMNS = {"results.tsv": ("name", "label", "value", "reads", "versus", "command"), "reviews.tsv": ("date", "stage", "verdict", "by", "of", "note")}
HASH = 2  # how a folder is hashed in the locks and runs made now; one without the marker was made with the first way
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
LISTS = {"goal": ("see",), "question": ("needs", "see"), "experiment": ("needs", "uses", "see"), "build": ("needs", "commits", "tests", "see"),
         "reading": ("needs", "see"), "decision": ("about", "holds", "see")}  # the front matter keys that hold a list
TEXTS = ("title", "asks", "from", "replaces", "because", "cost", "waiting_on", "dropped", "answered")  # and those that hold one value


def complement(a, b):
    """Whether two lines test the same result against the same number from opposite sides: one bar, said twice."""
    return bool(a.get("test") and b.get("test")) and a["name"] == b["name"] and a["num"] == b["num"] and OPPOSITE[a["op"]] == b["op"]


def first_sentence(text, least=8):
    """The opening of a text: its first sentence, and the next ones while it is still too short to say anything."""
    out = ""
    for part in re.split(r"(?<=[.!?])\s+(?=[A-Z(])", flat(text)):
        out = (out + " " + part).strip()
        if len(out.split()) >= least:
            break
    return out


def bare(text):
    """Card prose as plain text, for where nothing is drawn: a link is its words, and emphasis is dropped."""
    text = re.sub(r"\[([^\]\n]+)\]\([^)\s]+\)", r"\1", str(text or ""))
    return re.sub(r"\*\*([^*\n]+)\*\*", r"\1", text)


def items(text):
    """The items of a slot written as a list, each with its continuation lines joined."""
    out = []
    for raw in str(text or "").splitlines():
        raw = raw.strip()
        if raw.startswith("- "):
            out.append(raw[2:].strip())
        elif raw and out:
            out[-1] += " " + raw
    return out


def moment(text):
    """A recorded day or time as a UTC datetime, or None."""
    text = str(text or "").strip()
    try:
        d = datetime.datetime.fromisoformat(text if len(text) > 10 else text + "T00:00:00")
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)


def day(value):
    """A recorded day as `2026-01-02`, or "" when it is not one."""
    text = value.isoformat() if isinstance(value, (datetime.date, datetime.datetime)) else str(value or "").strip()
    return text[:10] if DAY.match(text[:10]) and moment(text[:10]) else ""


def amount(value):
    """Whether a value is an amount of a resource: a number, finite and not negative."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def read(path, problems=None, where=None):
    """A file's text, with its line ends read as plain newlines and a byte-order mark left out. What cannot be read (a
    folder or a broken link where a file belongs, bytes that are not UTF-8) is a problem, and nothing stops on it."""
    try:
        data = open(path, "rb").read()
    except OSError as err:
        if problems is not None:
            problems.append(f"files: {where or path}: cannot be read as a file ({err.__class__.__name__})")
        return ""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        if problems is not None:
            problems.append(f"files: {where or path}: is not UTF-8 text")
        text = data.decode("utf-8", errors="replace")
    return text.lstrip("\ufeff").replace("\r\n", "\n")


def split(text):
    """A card's front matter and its body. The front matter sits between the first two lines that are exactly `---`,
    so a `---` inside a title or a slot is text like any other."""
    lines = text.split("\n")
    if lines[0].rstrip() != "---":
        raise ValueError("a card opens with ---")
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            return "".join(l + "\n" for l in lines[1:i]), "\n".join(lines[i + 1:])
    raise ValueError("the front matter is not closed by ---")


def join(fm, body):
    return "---\n" + fm + "---\n" + body


def symlinks(folder):
    """Every symbolic link under a folder. A link's target is outside what a hash of the folder covers."""
    out = []
    for top, dirs, files in os.walk(folder):
        out += [os.path.relpath(os.path.join(top, n), folder) for n in dirs + files if os.path.islink(os.path.join(top, n))]
    return sorted(out)


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def text_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def tree_hash(folder, how=HASH):
    """One hash over a folder: every file's path and bytes, each preceded by its length, so that no two folders give
    the same hash. The first way (`how` 1: the path, a newline, the bytes) is kept to verify what was made with it.
    What Python leaves when it imports a script is not part of the folder, in either way: a `__pycache__` folder with
    everything under it, and a `*.pyc` file wherever it sits."""
    h, walked = hashlib.sha256(), []
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d != "__pycache__"]  # as the walk goes: sorting the walk first would read them all
        walked.append((root, files))
    for root, files in sorted(walked):
        for name in sorted(f for f in files if not f.endswith(".pyc")):
            p = os.path.join(root, name)
            path, data = os.path.relpath(p, folder).encode(), open(p, "rb").read()
            h.update(path + b"\n" + data if how == 1 else len(path).to_bytes(8, "big") + path + len(data).to_bytes(8, "big") + data)
    return h.hexdigest()


def seal_of(record):
    return hashlib.sha256(json.dumps({k: v for k, v in record.items() if k != "seal"}, sort_keys=True).encode()).hexdigest()


def flat(text):
    return " ".join(str(text).split())


def parse(text):
    """A card is front matter, a description (the paragraph before the first slot), and `## Slot` sections. Slots keep their line breaks."""
    fm, body = split(text)
    slots = {k.strip(): v.strip() for k, v in re.findall(r"^## (.+?)\n(.*?)(?=^## |\Z)", body, flags=re.S | re.M)}
    return yaml.safe_load(fm) or {}, slots, flat(re.split(r"^## ", body, maxsplit=1, flags=re.M)[0])


def card(path):
    return parse(read(path))


def table(text, columns=(), problems=None, where=""):
    """The rows of a tab-separated file, each as {column: text}. A field is one line's text between two tabs. One that a
    spreadsheet wrapped in double quotes, with each quote inside written twice, is read without them; any other quote is
    a character like any other, so a label that opens with one breaks nothing. A row that does not have the header's
    columns is a problem, and is read as far as it goes."""
    def field(f):
        inner = f[1:-1]
        return inner.replace('""', '"') if len(f) >= 2 and f[0] == f[-1] == '"' and '"' not in inner.replace('""', "") else f
    rows = [[field(f) for f in line.split("\t")] for line in text.split("\n") if line.strip()]  # a line ends at a newline and nowhere else
    said = problems.append if problems is not None else (lambda _: None)
    if not rows:
        return []
    head = [h.strip() for h in rows[0]]
    missing = [c for c in columns if c not in head]
    if missing:
        said(f"files: {where}: its first row names the columns, and {', '.join(missing)} {'is' if len(missing) == 1 else 'are'} not among them")
    out = []
    for n, r in enumerate(rows[1:], 2):
        if len(r) != len(head):
            said(f"files: {where}: row {n} has {len(r)} columns, and the header has {len(head)}")
        out.append({**{c: "" for c in columns}, **dict(zip(head, r))})
    return out


def tsv(path, problems=None, where=""):
    return table(read(path, problems, where), COLUMNS.get(os.path.basename(path), ()), problems, where) if os.path.lexists(path) else []


def number(text):
    text = str(text).strip()  # plain digits only: not 1_0, not digits of another script, not nan or inf
    v = float(text) if NUMBER.fullmatch(text) else None
    return v if v is not None and math.isfinite(v) else None


def shown(row):
    """A result's value as a page shows it, the way its row says it reads: a share as a percentage, a difference in points."""
    reads, v = row.get("reads") or "", row["num"]
    if v is None or reads not in ("percent", "points"):
        return row["value"]
    text = f"{abs(v) * 100:.1f}".rstrip("0").rstrip(".")
    if reads == "percent":
        return ("\u2212" if v < 0 else "") + text + "%"
    sign = str(row["value"]).strip()[:1] if str(row["value"]).strip()[:1] in "+-" and float(text) != 0 else ""  # a difference keeps its sign, a distance has none
    return sign.replace("-", "\u2212") + text + (" point" if text == "1" else " points")


def ends(rows, row):
    """The ends of a result's interval: the rows named `<name>.low` and `<name>.high`, when the experiment has them."""
    by = {r["name"]: r for r in rows}
    return by.get(row["name"] + ".low"), by.get(row["name"] + ".high")


def is_end(rows, row):
    """Whether a row is the end of another row's interval, and so is shown with it."""
    names = {r["name"] for r in rows}
    return any(row["name"].endswith(e) and row["name"][: -len(e)] in names for e in (".low", ".high"))


def shown_with_interval(rows, row):
    """A result as a page shows it: its value, and its interval when the experiment recorded one."""
    low, high = ends(rows, row)
    bare = lambda r: shown(r).replace(" points", "").replace(" point", "")
    if low and high:
        return f"{shown(row)} ({bare(low)} to {bare(high)})"
    if high:
        return f"{shown(row)} (interval up to {bare(high)})"
    if low:
        return f"{shown(row)} (interval from {bare(low)})"
    return shown(row)


def alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def code_head(lab):
    """The commit the code repository is at, or None."""
    import subprocess
    code = os.path.join(lab.root, lab.cfg["code"]) if lab.cfg.get("code") else lab.root
    return subprocess.run(["git", "-C", code, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or None


def find_root(start=None):
    d = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.exists(os.path.join(d, "lab.toml")):
            return d
        if d == os.path.dirname(d):
            raise SystemExit("no lab.toml here or above: this is not a lab")
        d = os.path.dirname(d)


class Lab:
    def __init__(self, root=None):
        self.root = find_root(root)
        self.problems = []  # what could not be read as the model says; `lab check` reports them
        self.cfg = self._toml("lab.toml", "files")
        for key in ("name", "title", "library", "store", "store_host", "code", "code_url"):
            if key in self.cfg and not isinstance(self.cfg[key], str):
                self.problems.append(f"files: lab.toml: `{key}` is a text")
                del self.cfg[key]
        self.cfg.setdefault("name", os.path.basename(self.root))
        # The store holds `runs/` and `.incoming/`. With no `store:` it is the lab itself. Elsewhere, the lab's
        # `runs` is a link to `<store>/runs`, and a run is written under `.lab/running/` until it is moved there.
        self.store_root = os.path.normpath(os.path.join(self.root, self.cfg["store"])) if self.cfg.get("store") else self.root
        self.store = os.path.join(self.root, "runs")
        self.running = os.path.join(self.root, ".lab", "running")
        self.resources = self._resources()
        self.lines = self._log()
        self.glossary = self._glossary()
        self.goals, self.nodes = self._tree(), {}
        self.questions = [q for g in self.goals for q in g["questions"]]
        self.items = [x for q in self.questions for x in q["items"]]
        self.experiments = [x for x in self.items if x["type"] == "experiment"]
        self.builds = [x for x in self.items if x["type"] == "build"]
        self.readings = [x for x in self.items if x["type"] == "reading"]
        self.decisions = self._decisions()
        for n in self.goals + self.questions + self.items + self.decisions:
            n["title"], n["description"] = flat(n.get("title") or n["id"]), flat(n.get("description") or "")
            if n["type"] == "question":  # the question in full; a card without `asks:` has it as its title
                n["asks"] = flat(n.get("asks") or n["title"])
            self.nodes[n["id"]] = n
        self.runs = self._runs()
        for x in self.experiments:
            mine = sorted((r for r in self.runs if r.get("experiment") == x["id"]), key=lambda r: (str(r.get("started")), r["id"]))  # in the order they started
            x["trials"], x["runs"] = [r for r in mine if r["kind"] == "trial"], [r for r in mine if r["kind"] != "trial"]
            x["finished"] = next((r for r in x["runs"] if r["state"] == "finished"), None)  # the only source of its results
        self.results = {}
        for x in self.experiments:
            for row in x["results"]:
                self.results[row["ref"]] = row
        for q in self.questions:
            q["state"] = self._question_state(q)
        for x in self.items:  # needs look at earlier items, so builds and experiments are settled in tree order
            x["state"], x["next"], x["mine"] = {"build": self._build_state, "reading": self._reading_state, "experiment": self._experiment_state}[x["type"]](x)
        for row in self.results.values():  # a number may be used on a card once its experiment is reviewed, and until it is replaced
            x = self.nodes[row["experiment"]]
            row["usable"] = x["reviewed"] and x["state"] not in ("replaced", "dropped")

    # ---------------------------------------------------------------- reading

    def rel(self, path):
        return os.path.relpath(path, self.root)

    def _toml(self, name, check="resources"):
        path = f"{self.root}/{name}"
        try:
            return tomllib.loads(read(path, self.problems, name)) if os.path.lexists(path) else {}
        except tomllib.TOMLDecodeError as err:
            self.problems.append(f"{check}: {name}: cannot be read ({err})")
            return {}

    def _resources(self):
        """Each resource as its table says. What is not written as the model says is a problem, and is left out."""
        out = {}
        for name, r in self._toml("resources.toml").items():
            bad = lambda what: self.problems.append(f"resources: resources.toml: {name}: {what}")
            if not isinstance(r, dict):
                bad("a resource is a table, `[name]`, that says what it is in `what`")
                continue
            r = dict(r)
            if not isinstance(r.get("rules", []), list):
                bad("`rules` is a list of sentences")
                r["rules"] = []
            if "per_run" in r and not (amount(r["per_run"]) and r["per_run"] > 0):
                bad("`per_run` is an amount: a number above zero")
                del r["per_run"]
            if "granted" in r and not amount(r["granted"]):
                bad("`granted` is an amount: a number")
                del r["granted"]
            for key in ("from", "retired", "unit"):
                if key in r and not isinstance(r[key], str):
                    bad(f"`{key}` is a text" + (": the decision that set its amounts, as \"D1\"" if key == "from" else ""))
                    del r[key]
            out[str(name)] = r
        return out

    def _card(self, path, kind):
        where = self.rel(path)
        bad = lambda what: self.problems.append(f"cards: {where}: {what}")
        try:
            fm, slots, lead = parse(read(path, self.problems, where))
        except Exception as err:
            bad(f"cannot be read as front matter and slots ({err.__class__.__name__})")
            return {}, {}
        if not isinstance(fm, dict):
            bad("its front matter is not a list of `key: value` lines")
            fm = {}
        fm = {str(k): v for k, v in fm.items()}
        if "description" in fm:
            bad("the description is the paragraph under the front matter, not a `description:` field")
        fm["description"] = lead
        for key in ("id", "status", "state", "outcome"):
            if key in fm:
                bad(f"writes `{key}:`, which is worked out from the record")
                fm.pop(key)
        scalar = lambda v: isinstance(v, (str, int, float, datetime.date)) and not isinstance(v, bool)
        for key in LISTS[kind]:  # one value is a list of one; anything else that is not a list is a problem
            v = fm.get(key)
            items = [] if v is None else [v] if scalar(v) else v if isinstance(v, list) else None
            if items is None or not all(scalar(i) for i in items):
                bad(f"`{key}:` is a list, such as `{key}: [a, b]`")
                items = [i for i in (items or []) if scalar(i)]
            fm[key] = [str(i) for i in items]
        for key in TEXTS:
            if key in fm and fm[key] is not None and not isinstance(fm[key], (str, int, float, bool, datetime.date)):
                bad(f"`{key}:` holds one value, not a list")
                fm.pop(key)
            elif fm.get(key) is not None:
                fm[key] = str(fm[key])
        if kind == "experiment":
            over = fm.get("override")
            if over is not None and not isinstance(over, dict):
                bad("`override:` is `{resource: cap}`")
            fm["override"] = {}
            for name, cap in (over if isinstance(over, dict) else {}).items():
                if amount(cap):
                    fm["override"][str(name)] = cap
                else:
                    bad(f"override {name}: an override is a cap on a resource the experiment uses, as a number")
        if kind == "decision":
            raised = day(fm.get("date"))
            if not raised:
                bad("`date:` is the day the decision was raised, as 2026-01-02")
            fm["date"] = raised
            done = fm.get("decided")
            if done is not None and not (isinstance(done, dict) and day(done.get("date")) and str(done.get("with") or "").strip()):
                bad("`decided:` holds when and with whom, `{date: 2026-01-02, with: <name>}`, and is written by `lab decide`")
            fm["decided"] = {"date": day(done.get("date")), "with": str(done.get("with") or "")} if isinstance(done, dict) else None
            fm["decided_as_written"] = done
        return fm, slots

    def _log(self):
        lines, today, path = [], None, f"{self.root}/log.md"
        if not os.path.lexists(path):
            return lines
        for n, raw in enumerate(read(path, self.problems, "log.md").split("\n"), 1):
            if raw.startswith("## "):
                today = day(raw[3:]) if DAY.match(raw[3:].strip()) else None
                if not today:
                    self.problems.append(f"log: log.md line {n}: a heading is a day, `## 2026-01-02`; the lines under {raw.strip()!r} are not read")
            elif raw.startswith("#"):
                self.problems.append(f"log: log.md line {n}: the only headings are days, `## 2026-01-02`")
            elif raw.startswith("- ") and today:
                parts = [p.strip() for p in raw[2:].split("|")]
                time = parts.pop(0) if parts and CLOCK.match(parts[0]) and parts[0][:2] < "24" and parts[0][3:] < "60" else ""  # lines written before the kit kept the time have none
                if len(parts) < 3 or len(parts) > 4:
                    self.problems.append(f"log: log.md line {n}: a line is `- time | about | kind | what happened | so what`, under a `## date`, and holds no other |")
                    if len(parts) < 3:
                        continue
                    parts = parts[:3] + [" / ".join(parts[3:])]
                parts += [""] * (4 - len(parts))
                lines.append({"day": today, "time": time, "at": f"{today}T{time}:00+00:00" if time else today, "about": parts[0], "kind": parts[1], "what": parts[2], "so": parts[3], "line": n})
            elif raw.startswith("- "):
                if today is None and not any(p.startswith("log: log.md") for p in self.problems):
                    self.problems.append(f"log: log.md line {n}: a line is `- time | about | kind | what happened | so what`, under a `## date`")
        return lines

    def _glossary(self):
        out, group, path = [], None, f"{self.root}/GLOSSARY.md"
        if not os.path.lexists(path):
            return out
        for block in re.split(r"^(?=#{1,2} )", read(path, self.problems, "GLOSSARY.md"), flags=re.M):
            if block.startswith("# "):
                group = block[2:].strip()
            elif block.startswith("## "):
                head, _, rest = block[3:].partition("\n")
                code = re.search(r"^- code: (.+)$", rest, flags=re.M)
                definition = " ".join(l for l in rest.split("\n") if l.strip() and not l.startswith("- ")).strip()
                out.append({"term": head.strip(), "group": group, "definition": definition, "code": code.group(1).strip("` ") if code else ""})
        return out

    def _lines(self, text):
        """The lines of a Confirmed if or Refuted if slot: a sentence, and the one result it tests."""
        out = []
        for raw in text.splitlines():
            raw = raw.strip()
            if not raw.startswith("- "):
                if raw and out:
                    out[-1]["raw"] += " " + raw
                continue
            out.append({"raw": raw[2:].strip()})
        for l in out:
            m = LINE.match(flat(l["raw"]))
            l.update({"role": m.group("role"), "say": m.group("say"), "name": m.group("name"), "op": m.group("op"), "num": float(m.group("num")),
                      "test": f"{m.group('name')} {m.group('op')} {m.group('num')}"} if m else {"role": None, "say": re.sub(r"^(answer|readable|counts):\s*", "", flat(l["raw"])), "test": None})
        return out

    def _numbered(self, pattern, name, taken, what):
        """The cards a pattern finds, in the order of their numbers: (number, path). A folder whose name does not give a
        number is a problem and is not read; so is a second folder with a number already taken."""
        found = []
        for path in sorted(glob.glob(pattern)):
            m = re.search(name, path)
            if not m:
                self.problems.append(f"tree: {self.rel(path)}: its folder or file is named `{what}`, with a number; it is not read")
            else:
                found.append((int(m.group(1)), path))
        out = []
        for n, path in sorted(found):
            if n in taken:
                self.problems.append(f"tree: {self.rel(path)}: its name gives the number {n}, which {self.rel(taken[n])} already has; it is not read")
            else:
                taken[n] = path
                out.append((n, path))
        return out

    def _json(self, path):
        try:
            return json.loads(read(path, self.problems, self.rel(path)))
        except ValueError:
            return None

    def _lock(self, path):
        """An experiment's lock. One that cannot be read still locks: it is a problem, never a licence to lock again."""
        v = self._json(path)
        ok = isinstance(v, dict) and isinstance(v.get("card"), str) and isinstance(v.get("locked"), str) and moment(v["locked"]) and isinstance(v.get("trials", []), list)
        if not ok:
            self.problems.append(f"locks: {self.rel(path)}: cannot be read as a lock: when it was locked, the hash of what the experiment demands, the hash of plan/, and its trial runs")
            return {"locked": "", "commit": None, "card": None, "plan": None, "uses": None, "hash": 1, "trials": [], "unreadable": True}
        made = "kit" in v  # a lock this kit made says so, and holds all of what follows; an older one holds what it holds
        uses = v.get("uses") if isinstance(v.get("uses"), list) and all(isinstance(i, str) for i in v["uses"]) else None
        plan = v.get("plan") if isinstance(v.get("plan"), str) else None
        if made and (plan is None or uses is None or v.get("hash") != HASH or not isinstance(v["kit"], str)):
            self.problems.append(f"locks: {self.rel(path)}: is not the lock `lab lock` wrote: it holds the hash of plan/ (`plan`), the resources the experiment uses (`uses`) and how they were hashed (`hash`)")
        return {**v, "plan": plan, "uses": uses, "hash": HASH if v.get("hash") == HASH else 1, "trials": [str(i) for i in v.get("trials", []) if isinstance(i, (str, int))]}

    def _ledger(self, xdir):
        """What runs.tsv says of an experiment's runs, by run: its kind, when it started, and once it ended, how and with
        which seal; or that it was declared lost, with what it used and why."""
        path, out = f"{xdir}/runs.tsv", {}
        where = self.rel(path)
        if not os.path.lexists(path):
            return out
        rows = [line.split("\t") for line in read(path, self.problems, where).split("\n") if line.strip()]
        if rows and (len(rows[0]) < 6 or tuple(rows[0]) != LEDGER[:len(rows[0])]):
            self.problems.append(f"runs: {where}: its first row names the columns: {', '.join(LEDGER)}")
        for r in rows[1:]:
            row = dict(zip(LEDGER, r + [""] * (len(LEDGER) - len(r))))
            run, what = row["run"], row["what"]
            if len(r) < 6 or len(r) > len(LEDGER) or not RUN_ID.match(run) or row["kind"] not in ("run", "trial") or what not in ("started", "ended", "lost") or not moment(row["at"]):
                self.problems.append(f"runs: {where}: the row for {run[:40]!r} is not `run, kind, started|ended|lost, time, exit, seal, used, note`")
                continue
            e = out.setdefault(run, {"id": run, "kind": row["kind"], "started": None, "ended": None, "exit": None, "seal": None, "lost": "", "used": None})
            if (what == "started" and e["started"]) or (what != "started" and e["ended"]) or e["kind"] != row["kind"]:
                self.problems.append(f"runs: {where}: {run} is listed twice as {'started' if what == 'started' else 'ended'}")
            elif what == "started":
                e["started"] = row["at"]
            elif what == "lost":
                try:
                    used = json.loads(row["used"]) if row["used"] else {}
                except ValueError:
                    used = None
                if not flat(row["note"]) or not isinstance(used, dict) or not all(amount(v) for v in used.values()):
                    self.problems.append(f"runs: {where}: {run} is declared lost with no reason, or with a use that is not `{{\"<resource>\": <amount>}}`")
                    used = {}
                e.update(ended=row["at"], exit=-1, lost=flat(row["note"]) or "no reason given", used=used)
            else:
                if not re.fullmatch(r"-?[0-9]+", row["exit"]) or not re.fullmatch(r"[0-9a-f]{64}", row["seal"]):
                    self.problems.append(f"runs: {where}: {run} ended with the exit {row['exit']!r} and the seal {row['seal'][:12]!r}: a number, and a hash")
                    continue
                e.update(ended=row["at"], exit=int(row["exit"]), seal=row["seal"])
        return out

    def _tree(self):
        goals = []
        for gn, gp in self._numbered(f"{self.root}/goals/*/goal.md", r"/G(\d+)-[^/]+/goal\.md$", {}, "G<n>-<name>"):
            gdir, gid = os.path.dirname(gp), f"G{gn}"
            fm, gslots = self._card(gp, "goal")
            goal = {"title": gid, "description": "", "see": [], **fm, "id": gid, "type": "goal", "slots": gslots, "path": self.rel(gp), "dir": self.rel(gdir), "questions": []}
            goal["state"] = "dropped" if fm.get("dropped") else "reached" if fm.get("reached") else "active"
            for qn, qp in self._numbered(f"{gdir}/*/question.md", r"/Q(\d+)-[^/]+/question\.md$", {}, "Q<n>-<name>"):
                qdir, qid = os.path.dirname(qp), f"{gid}.Q{qn}"
                qfm, qslots = self._card(qp, "question")
                q = {"title": qid, "description": "", "needs": [], "see": [], "asks": "", **qfm, "id": qid, "type": "question", "goal": gid, "slots": qslots,
                     "path": self.rel(qp), "dir": self.rel(qdir), "items": []}
                taken = {}
                steps = [s for kind in STEPS for s in self._numbered(f"{qdir}/*/{kind}.md", r"/(\d+)-[^/]+/[a-z]+\.md$", taken, "<n>-<name>")]
                for xn, xp in sorted(steps):
                    xdir, kind = os.path.dirname(xp), os.path.basename(xp)[:-3]
                    xid = f"{qid}.{xn}"
                    xfm, xslots = self._card(xp, kind)
                    x = {"title": xid, "description": "", "needs": [], "see": [], **xfm, "id": xid, "type": kind, "question": qid, "goal": gid, "slots": xslots,
                         "path": self.rel(xp), "dir": self.rel(xdir)}
                    if kind == "experiment":
                        x.setdefault("uses", [])
                        x.setdefault("override", {})
                        x["lines"] = {"confirmed": self._lines(xslots.get("Confirmed if", "")), "refuted": self._lines(xslots.get("Refuted if", ""))}
                        x["arms"] = [tuple(p.strip() for p in (i.split(": ", 1) + [""])[:2]) for i in items(xslots.get("Arms", ""))]  # (its name, what it is)
                        x["lock"] = self._lock(f"{xdir}/lock.json") if os.path.lexists(f"{xdir}/lock.json") else None
                        x["listed"] = self._ledger(xdir)
                        x["reviews"] = tsv(f"{xdir}/reviews.tsv", self.problems, self.rel(f"{xdir}/reviews.tsv"))
                        x["results"] = [{**r, "ref": f"{xid}:{r.get('name')}", "experiment": xid, "num": number(r.get("value", ""))}
                                        for r in tsv(f"{xdir}/results.tsv", self.problems, self.rel(f"{xdir}/results.tsv"))]
                    elif kind == "build":
                        x.setdefault("commits", [])
                        x.setdefault("tests", [])
                    q["items"].append(x)
                goal["questions"].append(q)
            goals.append(goal)
        for d in sorted(glob.glob(f"{self.root}/goals/*/")):  # a folder of cards with no card of its own is read by nothing
            if not os.path.lexists(f"{d}goal.md") and glob.glob(f"{d}*/question.md"):
                self.problems.append(f"tree: {self.rel(d.rstrip('/'))}: holds questions and has no goal.md; nothing under it is read")
            for q in sorted(glob.glob(f"{d}*/")) if os.path.lexists(f"{d}goal.md") else []:
                if not os.path.lexists(f"{q}question.md") and any(glob.glob(f"{q}*/{kind}.md") for kind in STEPS):
                    self.problems.append(f"tree: {self.rel(q.rstrip('/'))}: holds steps and has no question.md; nothing under it is read")
        return goals

    def _decisions(self):
        """Every decision: what there was to discuss with the operator, and once settled, what was decided and why."""
        out = []
        for n, path in self._numbered(f"{self.root}/decisions/D*.md", r"/D(\d+)-[^/]+\.md$", {}, "D<n>-<name>.md"):
            fm, slots = self._card(path, "decision")
            d = {"title": f"D{n}", "about": [], "holds": [], "decided": None, "date": "", "see": [], **fm, "id": f"D{n}", "type": "decision", "slots": slots,
                 "path": self.rel(path), "dir": self.rel(os.path.dirname(path))}
            d["state"] = "decided" if d["decided"] else "open"
            out.append(d)
        return out

    def _runs(self):
        out = []
        for rj in sorted(glob.glob(f"{self.store}/*/run.json") + glob.glob(f"{self.running}/*/run.json"), key=lambda p: os.path.basename(os.path.dirname(p))):
            d = os.path.dirname(rj)
            r = self._json(rj)
            ok = (isinstance(r, dict) and r.get("id") == os.path.basename(d) and isinstance(r.get("experiment"), str) and r.get("kind") in ("run", "trial")
                  and isinstance(r.get("started"), str) and moment(r["started"]) and isinstance(r.get("files", {}), dict)
                  and (r.get("ended") is None or (isinstance(r["ended"], str) and moment(r["ended"]))) and isinstance(r.get("used") or {}, dict) and isinstance(r.get("cap") or {}, dict))
            if not ok:
                self.problems.append(f"runs: {self.rel(rj)}: cannot be read as the record of the run its folder names")
                continue
            r.setdefault("files", {})
            for key in ("closed", "changed"):
                if r.get(key) is not None and not isinstance(r[key], str):
                    self.problems.append(f"runs: {self.rel(rj)}: `{key}` is a sentence")
                    r[key] = flat(str(r[key]))
            if r.get("exit") is not None and (not isinstance(r["exit"], int) or isinstance(r["exit"], bool)):
                self.problems.append(f"runs: {self.rel(rj)}: `exit` is the number the command ended with")
                r["exit"] = -1
            r["how"] = HASH if r.get("hash") == HASH else 1
            r["lost"] = ""
            r["dir"] = self.rel(d)
            r["local"] = d.startswith(self.running)
            r["missing"] = False
            r["present"] = [p for p in r["files"] if os.path.exists(os.path.join(d, p))]
            r["state"] = "running" if not r.get("ended") else "finished" if r.get("exit") == 0 else "failed"
            r["orphan"] = r["state"] == "running" and r.get("host") == os.uname().nodename and not alive(r.get("pid"))
            note = d + ".unpublished"
            r["unpublished"] = read(note).strip() if os.path.exists(note) else ""
            out.append(r)
        here = {r["id"] for r in out}
        for x in self.experiments:  # a run the ledger lists and the store does not hold: known to have run, with nothing to read
            for e in x["listed"].values():
                if e["id"] not in here and e["started"]:
                    out.append({**e, "experiment": x["id"], "dir": os.path.join("runs", e["id"]), "local": False, "missing": True, "present": [], "files": {}, "orphan": False,
                                "unpublished": "", "cap": {}, "lock": None, "plan": None, "changed": "", "host": None, "pid": None, "how": HASH,
                                "closed": f"declared lost: {e['lost']}" if e["lost"] else "", "used_by_hand": sorted(e["used"] or {}),
                                "state": "running" if not e["ended"] else "finished" if e["exit"] == 0 else "failed"})
        return out

    # ---------------------------------------------------------------- worked out

    def _goal_of(self, q):
        return next(g for g in self.goals if g["id"] == q["goal"])

    def live(self, nodes):
        """The goals or questions still pursued: what was dropped stays in the record and off the working pages."""
        return [n for n in nodes if n["state"] != "dropped"]

    def question_of(self, ident):
        m = re.match(r"(G\d+\.Q\d+)", ident)
        return self.nodes.get(m.group(1)) if m else None

    def open_decisions(self):
        return [d for d in self.decisions if d["state"] == "open"]

    def holding(self, ident):
        """The open decisions that hold this node: a decision holds what it lists, and everything under it."""
        return [d for d in self.open_decisions() if any(ident == h or ident.startswith(h + ".") for h in d["holds"])]

    def settled(self, node):
        """Whether the decision a goal or a question came from has been settled."""
        return self.nodes.get(str(node.get("from")), {}).get("state") == "decided"

    def settled_for(self, ident):
        """A settled decision that is about exactly this node: what a cap above the lab's amounts rests on."""
        return next((d for d in self.decisions if d["state"] == "decided" and ident in d["about"]), None)

    def held_by(self, decision):
        """The experiments and builds an open decision holds, still to be done."""
        if decision["state"] != "open":
            return []
        return [x for x in self.items if x["state"] not in ("done", "built", "dropped", "replaced") and any(x["id"] == h or x["id"].startswith(h + ".") for h in decision["holds"])]

    def metered(self, name):
        r = self.resources.get(name) or {}
        return amount(r.get("granted"))

    def granted_by(self, name):
        """The settled decision that set a metered resource's amounts, or None."""
        d = self.nodes.get(str((self.resources.get(name) or {}).get("from")))
        return d if d and d["type"] == "decision" and d["state"] == "decided" and name in d["about"] else None

    def cap(self, x, name):
        """What one run of this experiment may use of a resource: its override, or the lab's amount for one run."""
        return x["override"].get(name, (self.resources.get(name) or {}).get("per_run"))

    def other_use(self, name):
        """Use of a resource outside any run, such as a machine woken when nothing ran: [{date, amount, what}]."""
        rows = (self.resources.get(name) or {}).get("other_use") or []
        return [r for r in rows if isinstance(r, dict) and amount(r.get("amount"))] if isinstance(rows, list) else []

    def used(self, name):
        return sum(v for v in ((r.get("used") or {}).get(name, 0) for r in self.runs) if amount(v)) + sum(r["amount"] for r in self.other_use(name))

    def committed(self, name):
        """What the runs still going may yet use."""
        return sum(v for v in ((r.get("cap") or {}).get(name) or 0 for r in self.runs if r["state"] == "running") if amount(v))

    def left(self, name):
        return (self.resources.get(name) or {}).get("granted", 0) - self.used(name) - self.committed(name)

    def before_hash(self, x):
        return text_hash("\n".join(f"{k}\n{flat(x['slots'].get(k, ''))}" for k in BEFORE))

    def plan_hash(self, x, how=HASH):
        d = os.path.join(self.root, x["dir"], "plan")
        return tree_hash(d, how) if os.path.isdir(d) else "-"

    def content(self, x, stage, how=HASH):
        """One hash of what a review of this stage reads: the lines and the plan, or the results and the run they come
        from. The results are hashed as text, so the same rows with other line ends are the same rows."""
        if stage == "plan":
            return text_hash(self.before_hash(x) + self.plan_hash(x, how))[:16]
        rows = os.path.join(self.root, x["dir"], "results.tsv")
        return text_hash((text_hash(read(rows)) if os.path.isfile(rows) else "-") + str((x.get("finished") or {}).get("seal")))[:16]

    def reviewed(self, x, stage):
        """The last review of this stage, and whether what it read is still what is there. A failed results review is final."""
        rows = [r for r in x["reviews"] if r.get("stage") == stage]
        if stage == "results" and any(r.get("verdict") == "fail" for r in rows):
            return "fail", True
        if not rows:
            return None, False
        return rows[-1].get("verdict"), rows[-1].get("of") in (self.content(x, stage), self.content(x, stage, 1))  # a review made before folders were hashed as now still stands

    def lock_holds(self, x):
        """The lock holds what the experiment demands: its comparison, arms, cases, bars, outcomes and limits. The
        apparatus in plan/ is pinned by each run, and may change between runs while none has finished."""
        lock = x["lock"]
        return bool(lock) and lock.get("card") == self.before_hash(x) and (lock.get("uses") is None or sorted(lock["uses"]) == sorted(x["uses"]))

    def ticks(self, x):
        """Each line with whether it holds: True, False, or None while its result is not there."""
        own = {r["name"]: r for r in x["results"]}
        out = {}
        for side in ("confirmed", "refuted"):
            out[side] = []
            for l in x["lines"][side]:
                row = own.get(l.get("name"))
                ok = OPS[l["op"]](row["num"], l["num"]) if l["test"] and row and row["num"] is not None else None
                out[side].append({**l, "holds": ok, "row": row})
        for l in out["confirmed"]:  # a bar a refuted-if line already states from the other side: read once, there
            l["twice"] = any(complement(l, r) for r in out["refuted"])
        return out

    def outcome(self, x):
        """Confirmed when every confirmed-if line holds, refuted when any refuted-if line holds, unclear in between. None while a tested result is missing."""
        t = self.ticks(x)
        every = t["confirmed"] + t["refuted"]
        if not every or any(l["holds"] is None for l in every):
            return None
        if any(l["holds"] for l in t["refuted"]):
            return "refuted"
        return "confirmed" if t["confirmed"] and all(l["holds"] for l in t["confirmed"]) else "unclear"

    def replaced_by(self, ident):
        return next((x for x in self.experiments if x.get("replaces") == ident and not x.get("dropped")), None)

    def _question_state(self, q):
        if q.get("dropped") or self._goal_of(q).get("dropped"):
            return "dropped"
        if q.get("answer") in ("yes", "no"):
            return q["answer"]
        return "open" if self.settled(q) else "under discussion"

    def _blocked(self, x):
        """Why nothing under this item may move yet, or None."""
        q, g = self.nodes[x["question"]], self.nodes[x["goal"]]
        if g["state"] != "active":
            return f"{g['id']} is {g['state']}"
        if q["state"] == "under discussion":
            return f"the decision {q.get('from') or 'it comes from'} to be settled"
        if q["state"] != "open":
            return f"{q['id']} is {'answered ' + q['state'] if q['state'] in ('yes', 'no') else q['state']}"
        for need in x.get("needs") or []:
            n = self.nodes.get(need)
            if n and n.get("state") not in ("done", "built", "yes", "no"):
                return f"{need} {n['title']}"
        return None

    def _reading_state(self, r):
        """A reading is done once it says what was seen and what that suggests. Nothing locks it and nothing reviews it:
        it looks at what already exists, with no bar set in advance, so it can suggest and never confirm."""
        if r.get("dropped"):
            return "dropped", "", False
        if all(flat(r["slots"].get(k, "")) for k in ("Seen", "Suggests")):
            return "done", "", False
        held = self.holding(r["id"])
        if held:
            return "planned", f"the decision {held[0]['id']} to be settled", False
        why = self._blocked(r)
        if why:
            return "planned", why, False
        if not flat(r["slots"].get("Looks at", "")):
            return "planned", "say what it looks at, and where that is", True
        started = any(l["about"] == r["id"] for l in self.lines)
        return ("in progress" if started else "planned"), "read it; then write what was seen and what it suggests", True

    def _build_state(self, b):
        if b.get("dropped"):
            return "dropped", "", False
        if b["commits"]:
            return "built", "", False
        held = self.holding(b["id"])
        if held:
            return "planned", f"the decision {held[0]['id']} to be settled", False
        why = self._blocked(b)
        if why:
            return "planned", why, False
        started = any(l["about"] == b["id"] for l in self.lines)
        return ("in progress" if started else "planned"), "build it; then put its commits and its tests on the card", True

    def _experiment_state(self, x):
        """An experiment's state, what is next for it, and whether that is the agent's to do."""
        verdict, fresh = self.reviewed(x, "results")
        x["reviewed"] = bool(x["finished"] and x["results"] and verdict == "pass" and fresh)
        x["outcome"] = self.outcome(x) if x["reviewed"] else None
        if x.get("dropped"):
            return "dropped", "", False
        if self.replaced_by(x["id"]):
            return "replaced", "", False
        if verdict == "fail":
            return "review failed", "replace it with a new experiment, or drop it", True
        if x["reviewed"] and x["outcome"] and all(flat(x["slots"].get(k, "")) for k in ("Found", "Means")):
            return "done", "", False
        going = [r for r in x["runs"] + x["trials"] if r["state"] == "running"]
        if any(not r["orphan"] for r in going):
            return "running", "the run to end", False
        if going:
            return "planned", "close its run, whose process is gone (`lab runs` names it)", True
        if not x["finished"]:  # an open decision or a missing need holds what has not run; what has run is read and reviewed regardless
            held = self.holding(x["id"])
            if held:
                return "waiting", f"the decision {held[0]['id']} to be settled", False
            if x.get("waiting_on"):
                return "waiting", str(x["waiting_on"]), False
            why = self._blocked(x)
            if why:
                return "planned", why, False
        if not x["lock"]:
            lines = x["lines"]["confirmed"] + x["lines"]["refuted"]
            if not flat(x["slots"].get("Compares", "")) or not x["arms"] or not flat(x["slots"].get("Cases", "")) or not x["lines"]["confirmed"] or not x["lines"]["refuted"] or any(not l["test"] for l in lines):
                return "planned", "write what it compares, each arm, the cases, and its lines, each with the result it tests", True
            if not os.path.isdir(os.path.join(self.root, x["dir"], "plan")) or not os.listdir(os.path.join(self.root, x["dir"], "plan")):
                return "planned", "put the configuration and the code the run executes in plan/", True
            if any(self.metered(r) for r in x["uses"]) and self.reviewed(x, "plan") != ("pass", True):
                return "planned", "send the plan to a reviewer: its run uses a metered resource", True
            return "planned", "lock it", True
        if not x["finished"]:
            if x["runs"]:
                return "planned", "read why its last run failed; run it again under the same lock, or replace the experiment", True
            return "planned", "run it", True
        if not x["results"]:
            return "planned", "write a result row for each number its lines test", True
        missing = sorted({l["name"] for l in x["lines"]["confirmed"] + x["lines"]["refuted"] if l["test"]} - {r["name"] for r in x["results"]})
        if missing:
            return "planned", f"add the results its lines test: {', '.join(missing)}", True
        if not x["reviewed"]:
            return "planned", "send the results to a reviewer", True
        return "planned", "write Found and Means, naming its results", True

    def doing(self):
        """What the record says the agent is on: its last `doing` line, until a later line about the same card ends it."""
        last = None
        for l in self.lines:
            if l["kind"] == "doing":
                last = l
            elif last and l["kind"] in CLOSES and l["about"] == last["about"]:
                last = None
        if last and self.nodes.get(last["about"], {}).get("state") in ("done", "built", "dropped", "replaced", "yes", "no", "reached"):
            return None
        return last

    def last_record(self):
        """When the record last changed, as far as it says itself: the latest log line, lock, run start or run end."""
        seen = [l["at"] for l in self.lines if l["time"]] + [x["lock"]["locked"] for x in self.experiments if x["lock"] and x["lock"].get("locked")]
        seen += [r[k] for r in self.runs for k in ("started", "ended") if r.get(k)]
        times = [t for t in (moment(s) for s in seen) if t]
        return max(times) if times else None

    def chain(self, x):
        """The experiments this one replaced, the latest first."""
        out, old = [], x.get("replaces")
        while old in self.nodes and old not in [o["id"] for o in out]:
            out.append(self.nodes[old])
            old = self.nodes[old].get("replaces")
        return out

    def spent(self, x, name):
        """What every run and trial run of an experiment has used of a resource."""
        return sum(v for v in ((r.get("used") or {}).get(name, 0) for r in x["runs"] + x["trials"]) if amount(v))

    def yours(self):
        """Every experiment and build the agent can move now, with what is next on each."""
        return [x for x in self.items if x["mine"]]

    def since(self, day=None):
        """What happened since the last decision was recorded, or since a day."""
        last = max((i for i, l in enumerate(self.lines) if l["kind"] == "decision"), default=-1)
        if day:
            return [l for l in self.lines if l["day"] >= day and l["kind"] in CLOSES], day
        return [l for l in self.lines[last + 1:] if l["kind"] in CLOSES], (self.lines[last]["day"] if last >= 0 else None)

    def named(self, text, home=None):
        """Every result a card's text names: (the text as written, the result row or None)."""
        out = []
        for m in NAMED.finditer(text or ""):
            owner = m.group(1) or home
            out.append((m.group(0), self.results.get(f"{owner}:{m.group(2)}") if owner else None))
        return out

    def fill(self, text, home=None, show=None):
        """A card's text with each named result's value in place. A name that is not a result stays as written."""
        show = show or shown

        def one(m):
            owner = m.group(1) or home
            row = self.results.get(f"{owner}:{m.group(2)}") if owner else None
            return show(row) if row else m.group(0)
        return NAMED.sub(one, text or "")

    def at(self, path):
        """The node a file or a folder of the lab belongs to: a card, anything under an experiment, a run."""
        path = os.path.normpath(path)
        path = self.rel(path) if os.path.isabs(path) else path
        for n in self.nodes.values():
            if n["path"] == path:
                return n
        for r in self.runs:
            if (path + "/").startswith(r["dir"] + "/"):
                return self.nodes.get(r.get("experiment"))
        under = [n for n in self.nodes.values() if n["type"] != "decision" and (path + "/").startswith(n["dir"] + "/")]
        return max(under, key=lambda n: len(n["dir"]), default=None)

    def store_host(self):
        return os.environ.get("LAB_STORE_HOST") or self.cfg.get("store_host")
