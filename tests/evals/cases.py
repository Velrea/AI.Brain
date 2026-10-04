"""The eval cases: what a user asks of the seeded Brain, and what counts as right.

Every case starts from its own copy of the seeded Brain. Reads ask about the
stories, and their graders hold the stories' facts. Writes ask for something
to be recorded, corrected, renamed, merged, kept, or filed, or mention
something in passing, and their graders check the skill that fired, the
calls it made with their arguments, and the files it left. Pointers hand over
a file that only points to content kept elsewhere, and the cases for
documents filed already change one by hand before the run. A case tagged
`bash` files documents with the document skill's script, so it needs a
shell, which an eval run grants only where the host can sandbox it.
"""

import hashlib
from dataclasses import dataclass, field

import seed
from stories import ELSEWHERE, INBOX

TOOL = "mcp__plugin_brain_brain__"
IDS = seed.ids()
COIL_INVOICE = "vehicles/glidemaster-hovercart/service/2026-08-05-coil-replacement-invoice.txt"


@dataclass
class Case:
    name: str
    tags: list[str]
    prompt: str
    graders: dict[str, dict]
    inbox: dict[str, bytes] = field(default_factory=dict)
    """Files put in the run's `inbox/` folder, by name, each `{workspace}` in
    them made the run's folder as a file URL."""
    files: dict[str, bytes | None] = field(default_factory=dict)
    """Files written into the run's folder by path, once the seeded Brain and
    the inbox are there, replacing any there; None removes one."""
    max_turns: int = 30
    timeout_seconds: int = 600


def skill(name: str, *, fired: bool = True) -> dict:
    """The plugin's skill `name` was invoked, or never was."""
    grader = {"type": "tool_used", "tool": "Skill", "input_match": rf'"skill"\s*:\s*"(?:brain:)?{name}"'}
    return grader if fired else grader | {"min": 0, "max": 0, "arm": "both"}


def matching(*conditions: str) -> str:
    """A regex for a call's JSON matching every one of `conditions`: each a
    regex found anywhere in it, or a lookaround, taken as it is."""
    return "^" + "".join(c if c.startswith("(?") else f"(?=.*{c})" for c in conditions)


def write(*conditions: str, min: int = 1, max: int | None = None) -> dict:
    """`write` was called, between `min` and `max` times, with arguments
    matching every one of `conditions`."""
    grader = {"type": "tool_used", "tool": TOOL + "write", "input_match": matching(*conditions)}
    if min != 1:
        grader["min"] = min
    if max is not None:
        grader["max"] = max
    return grader


def never_write(*conditions: str) -> dict:
    return write(*conditions, min=0, max=0)


def searched() -> dict:
    return {"type": "tool_used", "tool": TOOL + "search"}


def answer(pattern: str, *, flags: str = "") -> dict:
    """The final reply matches `pattern`."""
    return {"type": "regex", "pattern": pattern} | ({"flags": flags} if flags else {})


def judged(criteria: str) -> dict:
    """A judge model votes the final reply PASS on `criteria`."""
    return {"type": "llm", "body": criteria}


def filed(glob: str, *, exists: bool = True) -> dict:
    """A document was filed, or none was, at a path inside `documents/` matching `glob`."""
    return {"type": "file_exists", "path": f"brain/documents/{glob}"} | ({} if exists else {"exists": False})


def shell(*conditions: str, min: int = 1, max: int | None = None) -> dict:
    """Bash was called, between `min` and `max` times, with a command matching
    every one of `conditions`."""
    grader = {"type": "tool_used", "tool": "Bash", "input_match": matching(*conditions)}
    if min != 1:
        grader["min"] = min
    if max is not None:
        grader["max"] = max
    return grader


def left(name: str) -> dict:
    """No shell command names the file `name`, so it stays where the case put it.

    A file grader cannot tell: it sees only files created during the run.
    """
    return shell(name.replace(".", r"\."), min=0, max=0)


def holds(name: str, value: str) -> str:
    """A regex for a JSON field `name` holding exactly the string `value`."""
    return rf'"{name}"\s*:\s*"{value}"'


def links(*slugs: str) -> str:
    """A regex for `links` holding every one of `slugs`."""
    return "".join(rf'(?=.*"links"\s*:\s*\[[^\]]*"{slug}")' for slug in slugs)


def revises(slug: str) -> str:
    """A regex for a revision of the entry created under `slug`."""
    return holds("entry", IDS[slug])


NEW = r'(?!.*"entry"\s*:\s*")'
"""A regex for a call that creates an entry rather than revising one."""

JOURNAL = holds("type", "journal")
ENTITY = holds("type", "entity")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


READS = [
    Case("current-potions", ["read", "fold", "snapshot"],
         "What potions am I taking right now, and how much of each?",
         {"query-fired": skill("query"), "searched": searched(),
          "three-drops": answer(r"3 drops|three drops", flags="i"),
          "current-set": judged(
              "PASS if the reply says the current potions are moonberry tonic at 3 drops nightly and starlight"
              " syrup at 1 teaspoon at lunch. FAIL if it gives 4 drops or 2 drops as the current moonberry dose,"
              " or lists thistle draught as still being taken.")}),
    Case("gnome-president", ["read", "fold"],
         "Who's the president of my gnome association these days?",
         {"query-fired": skill("query"), "grimsby": answer("Grimsby"),
          "not-pumpernickel": judged(
              "PASS if the reply says Mrs. Grimsby (Agatha Grimsby) is the president. FAIL if it says Mr."
              " Pumpernickel is the current president.")}),
    Case("corrected-odometer", ["read", "revision"],
         "What did the hovercart's odometer read at its float inspection in June?",
         {"query-fired": skill("query"), "corrected": answer(r"41,?020"),
          "not-the-old-figure": judged(
              "PASS if the reply gives 41,020 leagues as the reading; it may mention that 41,200 was recorded"
              " first and corrected. FAIL if it gives 41,200 leagues as the reading.")}),
    Case("goblin-visits", ["read", "fold"],
         "How many times has the chimney goblin got into the cottage, and what's being done about it?",
         {"query-fired": skill("query"), "searched": searched(),
          "three-and-the-plan": judged(
              "PASS if the reply says the goblin has got in three times (June 20, July 22, September 18), and that"
              " the roofers (Thatch & Sons, or Old Man Thatch) are coming back on October 8 to fit a finer mesh"
              " under the cap's guarantee. Dates in any format count. FAIL if it gives a count other than three,"
              " or leaves out the October 8 return visit.")}),
    Case("open-promise", ["read", "commitments"],
         "What have I promised Professor Quibblesworth that's still open?",
         {"query-fired": skill("query"), "glow-spec": answer(r"2026-10-15|October 15|15 October|Oct\.? 15", flags="i"),
          "only-what-is-open": judged(
              "PASS if the reply names the glow-in-the-dark variant spec, due 2026-10-15, as the open promise. FAIL"
              " if it presents the lens design draft (due 2026-06-30, sent on time) as still open.")}),
    Case("moonbeam-yield-now", ["read", "fold", "snapshot"],
         "What's Project Moonbeam's juice yield now?",
         {"query-fired": skill("query"), "seventy-eight": answer(r"78\s*%|78 percent", flags="i"),
          "latest": judged(
              "PASS if the reply gives 78% as the current yield. FAIL if it gives 62% or 71% as the current"
              " yield.")}),
    Case("moonbeam-budget-left", ["read", "fold"],
         "How much of the Moonbeam budget is left?",
         {"query-fired": skill("query"),
          "left": judged(
              "PASS if the reply says about $23,600 is left of a $55,000 budget ($31,400 spent, as of the August"
              " 19 review). FAIL if it works from a $50,000 budget, such as saying $18,600 is left.")}),
    Case("contract-notice", ["read", "documents"],
         "How much notice do we have to give to end the Glorp contract?",
         {"query-fired": skill("query"), "thirty-days": answer(r"30 days|thirty days", flags="i")}),
    Case("contract-where", ["read", "documents"],
         "Where's the Glorp Logistics contract filed?",
         {"query-fired": skill("query"),
          "path": answer(r"work/project-moonbeam/contracts/2026-07-01-glorp-logistics-contract\.txt")}),
    Case("dragon-damage", ["read", "merge"],
         "What has Sir Fluffington set fire to or damaged?",
         {"query-fired": skill("query"), "curtains": answer("curtain", flags="i"),
          "lampshade": answer("lampshade", flags="i")}),
    Case("dragon-weight", ["read", "alias"],
         "How much does my dragon weigh now?",
         {"query-fired": skill("query"), "weight": answer(r"4\.9"),
          "latest": judged("PASS if the reply gives 4.9 lb as his current weight. FAIL if it gives 4.2 lb as current.")}),
    Case("glorp-co-invoice", ["read", "alias"],
         "Did we ever pay that Glorp Co invoice?",
         {"query-fired": skill("query"),
          "cancelled": judged(
              "PASS if the reply says the $84 Glorp Co charge was not paid because Glorp Logistics cancelled it"
              " (Glorp Co being its billing name). FAIL if it says the invoice was paid, or that it is still"
              " disputed and unresolved.")}),
    Case("insurance-policy", ["read"],
         "What's my hovercart insurance policy number, and when does it run out?",
         {"query-fired": skill("query"), "number": answer("FW-77-ZB"),
          "end": answer(r"31 December|December 31|2026-12-31|Dec\.? 31", flags="i")}),
    Case("two-dr-js", ["read", "ambiguous"],
         "When did I last see Dr J?",
         {"query-fired": skill("query"),
          "tells-them-apart": judged(
              "PASS if the reply recognizes there are two people called Dr J, Dr. Jekyll and Dr. Jellybean, and"
              " either answers for both or asks which one is meant. FAIL if it answers for only one of them"
              " without noting the other.")}),
    Case("nothing-recorded", ["read", "negative"],
         "When did I take Sir Fluffington skydiving?",
         {"query-fired": skill("query"), "searched": searched(), "wrote-nothing": never_write(".*"),
          "says-none": judged(
              "PASS if the reply says the Brain has no record of Sir Fluffington going skydiving. FAIL if it"
              " gives a date or details of a skydiving trip.")}),
]

WRITES = [
    Case("record-vet-visit", ["write", "journal"],
         "Record this: on 2026-10-02 I took Sir Fluffington to Dr. Jellybean because he was sneezing glitter. She"
         " said it's an allergy to the glitter in the craft drawer: no treatment, just keep the drawer shut. The"
         " visit cost $45.",
         {"journal-fired": skill("journal"),
          "the-entry": write(NEW, JOURNAL, holds("event_date", "2026-10-02"), links("sir-fluffington", "dr-jellybean"),
                             r'"body"\s*:\s*"[^"]*\$?45'),
          "triage-description": write(NEW, JOURNAL, r'"description"\s*:\s*"[^"]*[Gg]litter'),
          "one-entry": write(NEW, JOURNAL, max=1),
          "no-new-subjects": never_write(NEW, ENTITY)}),
    Case("record-briefly", ["write", "journal"],
         "I had the windscreen on my hovercart replaced today at Gizmo's Garage, $210 out of pocket. Record it.",
         {"journal-fired": skill("journal"),
          "recorded-without-asking": write(NEW, JOURNAL, links("glidemaster-hovercart", "gizmos-garage"), r"210"),
          "no-new-subjects": never_write(NEW, ENTITY)}),
    Case("passing-mention", ["write", "journal", "unprompted"],
         "Ugh, I had to chase the chimney goblin out of the kitchen again last night with a broom. That's the"
         " fourth time now. Anyway, what's a good way to cook turnips?",
         {"journal-fired": skill("journal"),
          "recorded-it": write(NEW, JOURNAL, links("chimney-goblin")),
          "no-new-subjects": never_write(NEW, ENTITY)}),
    Case("no-record-for-chitchat", ["write", "negative"],
         "What's a good name for a garden gnome?",
         {"journal-not-fired": skill("journal", fired=False), "wrote-nothing": never_write(".*")}),
    Case("new-person", ["write", "entity"],
         "Record that on 2026-10-01 Ozwald Fizzlewhip, the potion inspector from the Ministry of Tonics,"
         " inspected Dr. Jekyll's moonberry tonic stock at the Lantern Street Apothecary and passed it.",
         {"journal-fired": skill("journal"),
          "made-the-person": write(NEW, ENTITY, r'"slug"\s*:\s*"[a-z0-9-]*fizzlewhip'),
          "person-first": {"type": "tool_order",
                           "before": {"tool": TOOL + "write", "input_match": matching(NEW, ENTITY, "fizzlewhip")},
                           "after": {"tool": TOOL + "write", "input_match": matching(NEW, JOURNAL)}},
          "entry-links-them": write(NEW, JOURNAL, r'(?=.*"links"\s*:\s*\[[^\]]*fizzlewhip)', links("dr-jekyll")),
          "jekyll-reused": never_write(NEW, ENTITY, r'"slug"\s*:\s*"[a-z0-9-]*jekyll')}),
    Case("add-alias", ["write", "entity"],
         "Around the office everyone calls Professor Quibblesworth \"Quibbs\". Make sure the Brain knows that name.",
         {"entity-fired": skill("entity"),
          "alias-added": write(ENTITY, revises("prof-quibblesworth"), r'"aliases"\s*:\s*\[[^\]]*"Quibbs"'),
          "no-new-entity": never_write(NEW, ENTITY)}),
    Case("merge-duplicates", ["write", "entity", "merge"],
         "Glorp Co and Glorp Logistics are the same company. Merge them in the Brain.",
         {"entity-fired": skill("entity"),
          "merged-into-the-linked-one": write(ENTITY, revises("glorp-logistics"), holds("slug", "glorp-co")),
          "not-the-other-way": never_write(revises("glorp-co")),
          "no-new-entity": never_write(NEW, ENTITY)}),
    Case("correct-a-date", ["write", "revision"],
         "Correction: the Moonbeam board demo was on September 3rd, not September 2nd.",
         {"journal-fired": skill("journal"),
          "revised": write(JOURNAL, revises("2026-09-02-moonbeam-board-demo"), holds("event_date", "2026-09-03")),
          "no-new-entry": never_write(NEW, JOURNAL)}),
    Case("correct-and-add", ["write", "revision"],
         "About the hovercart's coil replacement in August: the bill was actually $1,340, not $1,240; I misread"
         " it. And separately, on 2026-10-01 Gizmo rang to say that coil model has been recalled, and he'll swap"
         " it for free on 2026-10-20.",
         {"journal-fired": skill("journal"),
          "corrected": write(JOURNAL, revises("2026-08-05-hovercart-coil-replaced"), r"1,?340"),
          "new-entry-follows-on": write(NEW, JOURNAL, holds("event_date", "2026-10-01"),
                                        links("2026-08-05-hovercart-coil-replaced")),
          "recall-not-in-the-correction": never_write(revises("2026-08-05-hovercart-coil-replaced"), "[Rr]ecall")}),
    Case("follow-on-entry", ["write", "journal", "links"],
         "Record that Thatch & Sons came early: on 2026-10-02 they fitted the finer mesh on the chimney cap, at"
         " no charge, as promised after the goblin's last visit.",
         {"journal-fired": skill("journal"),
          "links-what-it-follows": write(NEW, JOURNAL, holds("event_date", "2026-10-02"),
                                         links("thatch-and-sons", "2026-09-18-chimney-goblin-third-visit"))}),
    Case("keep-a-secret-out", ["write", "journal", "secret"],
         "Note that on 2026-10-02 I changed the code on the garden-gate gnome lock at the cottage to 7741-moon.",
         {"journal-fired": skill("journal"),
          "recorded": write(NEW, JOURNAL, links("wobblestone-cottage")),
          "code-not-written": never_write("7741-moon")}),
    Case("snapshot-on-request", ["write", "snapshot"],
         "Work out what potions I'm on now, and save that as a snapshot so we don't have to work it out again.",
         {"snapshot-fired": skill("snapshot"),
          "kept": write(NEW, holds("type", "snapshot"), r'"scope"\s*:\s*"', links("potions"),
                        r'"body"\s*:\s*"[^"]*(3|three) drops', "[Ss]tarlight"),
          "no-thistle-as-current": judged(
              "PASS if the reply reports moonberry tonic at 3 drops nightly and starlight syrup at 1 teaspoon at"
              " lunch as the current potions. FAIL if it reports thistle draught as current, or 4 drops of"
              " moonberry tonic.")}),
    Case("ask-which-dr-j", ["write", "ambiguous"],
         "Record that Dr J rang today and said everything looks fine.",
         {"wrote-nothing": never_write(".*"),
          "asks": judged(
              "PASS if the reply asks which Dr J is meant, Dr. Jekyll or Dr. Jellybean, before recording anything."
              " FAIL if it says it recorded an entry.")}),
]

COIL_COPY = (seed.BRAIN / "documents" / COIL_INVOICE).read_bytes()
TRIM_RECEIPT = INBOX["2026-09-24-gizmo-hover-trim-receipt.txt"].encode()

FILING = [
    Case("file-beside-its-like", ["write", "documents", "bash"],
         "File inbox/2026-09-24-gizmo-hover-trim-receipt.txt in the Brain.",
         {"document-fired": skill("document"),
          "filed-beside-the-coil-invoice": filed("vehicles/glidemaster-hovercart/service/*"),
          "its-entry": write(NEW, holds("type", "document"), holds("sha256", sha256(TRIM_RECEIPT)),
                             r'"path"\s*:\s*"vehicles/glidemaster-hovercart/service/', links("glidemaster-hovercart")),
          "journal-records-the-capture": write(NEW, JOURNAL, r'(?=.*"links"\s*:\s*\[[^\]]*"2026-09-24)')},
         inbox={"2026-09-24-gizmo-hover-trim-receipt.txt": TRIM_RECEIPT}),
    Case("file-a-folder", ["write", "documents", "bash"],
         "File everything in the inbox folder in the Brain.",
         {"document-fired": skill("document"),
          "letter-with-the-glorp-papers": filed("work/project-moonbeam/**"),
          "receipt-with-the-gnome-papers": filed("home/wobblestone-cottage/gnome-association/*"),
          "two-entries": write(NEW, holds("type", "document"), min=2, max=2)},
         inbox={name: INBOX[name].encode() for name in ("2026-09-22-glorp-rate-letter.txt",
                                                        "2026-10-01-gnome-dues-receipt.txt")}),
    Case("refuse-a-duplicate", ["write", "documents", "bash"],
         "File inbox/coil-invoice-scan.txt in the Brain.",
         {"document-fired": skill("document"),
          "no-entry": never_write(holds("type", "document")),
          "says-where-it-is": answer(COIL_INVOICE.replace(".", r"\.").rsplit("/", 1)[0])},
         inbox={"coil-invoice-scan.txt": COIL_COPY}),
    Case("ask-where-nothing-is-like-it", ["write", "documents", "bash"],
         "File inbox/telescope-warranty.txt in the Brain.",
         {"document-fired": skill("document"),
          "nothing-filed-yet": filed("**/*telescope*", exists=False),
          "offers-paths": judged(
              "PASS if the reply offers two or three places to file the telescope warranty, with one recommended,"
              " and asks which to use. FAIL if it says the warranty was filed.")},
         inbox={"telescope-warranty.txt": INBOX["telescope-warranty.txt"].encode()}),
]

BUDGET_TRACKER = "moonbeam-budget-tracker.zsheet"
BUDGET_ADDRESS = r'"address"\s*:\s*"https://sheets\.zorblax\.invalid/d/7Qx2mB9kLr'
COIL_CERTIFICATE = "2026-08-05-coil-warranty-certificate.txt"
COIL_CERTIFICATE_BYTES = ELSEWHERE[COIL_CERTIFICATE].encode()
CERTIFICATE_ADDRESS = r'"address"\s*:\s*"[^"]*elsewhere/' + COIL_CERTIFICATE.replace(".", r"\.")


POINTERS = [
    Case("pointer-out-of-reach", ["write", "documents", "pointer"],
         f"File inbox/{BUDGET_TRACKER} in the Brain.",
         {"document-fired": skill("document"),
          "nothing-filed": filed("**/*budget*", exists=False),
          "nothing-recorded": never_write(),
          "pointer-left": left(BUDGET_TRACKER),
          "asks-what-it-holds": judged(
              "PASS if the reply says the file only points to a spreadsheet kept elsewhere that could not be"
              " reached, and asks the user what it holds. FAIL if it says the file was filed or recorded.")},
         inbox={BUDGET_TRACKER: INBOX[BUDGET_TRACKER].encode()}),
    Case("pointer-with-what-it-holds", ["write", "documents", "pointer", "bash"],
         f"File inbox/{BUDGET_TRACKER} in the Brain. It's the Moonbeam budget tracker Prof. Quibblesworth"
         " keeps; it shows $38,200 of the $55,000 spent as of today.",
         {"document-fired": skill("document"),
          "filed-with-the-budget-sheet": filed("work/project-moonbeam/**/*budget*"),
          "its-entry": write(NEW, holds("type", "document"), holds("sha256", sha256(INBOX[BUDGET_TRACKER].encode())),
                             BUDGET_ADDRESS, "38,200", links("project-moonbeam"))},
         inbox={BUDGET_TRACKER: INBOX[BUDGET_TRACKER].encode()}),
    Case("pointer-to-a-file-here", ["write", "documents", "pointer", "bash"],
         "File inbox/coil-warranty.url in the Brain.",
         {"document-fired": skill("document"),
          "filed-beside-the-coil-invoice": filed("vehicles/glidemaster-hovercart/service/*warranty*"),
          "its-entry": write(NEW, holds("type", "document"), CERTIFICATE_ADDRESS, "2028",
                             r'"path"\s*:\s*"vehicles/glidemaster-hovercart/service/', links("glidemaster-hovercart")),
          "what-it-names-never-filed": shell(r"\bstore\b", COIL_CERTIFICATE.replace(".", r"\."), min=0, max=0),
          "what-it-names-never-removed": shell(COIL_CERTIFICATE.replace(".", r"\."),
                                               r"(?:\brm\b|\bdel\b|\bmv\b|Remove-Item|Move-Item)", min=0, max=0)},
         inbox={"coil-warranty.url": INBOX["coil-warranty.url"].encode()},
         files={f"elsewhere/{COIL_CERTIFICATE}": COIL_CERTIFICATE_BYTES}),
]

BUDGET_SHEET = "work/project-moonbeam/budget/2026-08-19-moonbeam-budget-sheet.txt"
BUDGET_SHEET_EDITED = (seed.BRAIN / "documents" / BUDGET_SHEET).read_bytes().replace(
    b"Freight: $2,700\nSpent: $31,400", b"Freight: $2,700\nSecond lens: $4,600\nSpent: $36,000")
GNOME_NOTICE = "home/wobblestone-cottage/gnome-association/2026-09-02-gnome-height-notice.txt"
GNOME_NOTICE_MOVED = "home/wobblestone-cottage/2026-09-02-gnome-height-notice.txt"
CHECKED = shell(r"documents\.py", r"\bcheck\b")
NO_NEW_DOCUMENT = never_write(NEW, holds("type", "document"))

FILED_ALREADY = [
    Case("record-an-edited-document", ["write", "documents", "bash"],
         "I updated the Moonbeam budget sheet in the Brain's documents. Record the change.",
         {"document-fired": skill("document"),
          "checked": CHECKED,
          "revised-with-its-new-hash": write(revises("2026-08-19-moonbeam-budget-sheet"),
                                             holds("sha256", sha256(BUDGET_SHEET_EDITED))),
          "no-new-document-entry": NO_NEW_DOCUMENT},
         files={f"brain/documents/{BUDGET_SHEET}": BUDGET_SHEET_EDITED}),
    Case("check-the-documents", ["write", "documents", "bash"],
         "Check my filed documents for anything that changed.",
         {"document-fired": skill("document"),
          "checked": CHECKED,
          "moved-to-its-new-path": write(revises("2026-09-02-gnome-height-notice-letter"),
                                         holds("path", GNOME_NOTICE_MOVED.replace(".", r"\."))),
          "no-new-document-entry": NO_NEW_DOCUMENT},
         files={f"brain/documents/{GNOME_NOTICE}": None,
                f"brain/documents/{GNOME_NOTICE_MOVED}": (seed.BRAIN / "documents" / GNOME_NOTICE).read_bytes()}),
]

CASES = READS + WRITES + FILING + POINTERS + FILED_ALREADY
