"""Writes the stories into a Brain folder, the same bytes every time.

The stories go through the core module's own write path and the document
skill's own filing, so the seeded Brain is one the plugin could have written:
every slug, link, revision, and filed document passes the checks a live
session's would. Only the clock and the random bits of each id are fixed, so
two builds are identical, file names included.

    python tests/evals/seed.py

rebuilds `tests/evals/brain/`, which is checked in. `tests/test_seed.py`
checks that a fresh build still matches it.
"""

import datetime as dt
import json
import random
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent.parent / "plugin"
sys.path[:0] = [str(PLUGIN), str(PLUGIN / "skills" / "document" / "scripts"), str(HERE)]

from brain.write import Writer  # noqa: E402
from documents import Documents  # noqa: E402
from stories import STORIES, Document, Entity, Journal, Revision, Snapshot  # noqa: E402

BRAIN = HERE / "brain"
SEED = 20260603
"""Fixes the random bits of every id the seed writes."""


def build(brain: Path) -> None:
    """Writes every story into `brain`, which must not exist yet."""
    brain.mkdir(parents=True)
    steps = sorted(
        ((step.on, n, machine, step) for machine, story in STORIES.items() for n, step in enumerate(story)),
        key=lambda item: (item[0], item[1], item[2]),
    )
    rng = random.Random(SEED)
    with tempfile.TemporaryDirectory() as temp, mock.patch("os.urandom", rng.randbytes):
        temp = Path(temp)
        clocks = {machine: _Clock() for machine in STORIES}
        writers = {
            machine: Writer(brain, temp / machine, clock=clocks[machine]) for machine in STORIES
        }
        for on, _, machine, step in steps:
            clocks[machine].advance_to(on)
            _write(writers[machine], brain, temp, step)


class _Clock:
    """A machine's clock: each step it writes is recorded a minute after the
    last, from 20:00 UTC on the day of the step."""

    def __init__(self):
        self.now = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)

    def advance_to(self, day: str) -> None:
        evening = dt.datetime.fromisoformat(f"{day}T20:00:00+00:00")
        self.now = max(evening, self.now + dt.timedelta(minutes=1))

    def __call__(self) -> dt.datetime:
        return self.now


def _write(writer: Writer, brain: Path, temp: Path, step) -> None:
    if isinstance(step, Entity):
        writer.write(
            type="entity", version=1, slug=step.slug, event_date=step.on, description=step.name, body=step.body,
            aliases=list(step.aliases), details={"kind": step.kind},
        )
    elif isinstance(step, Journal):
        writer.write(
            type="journal", version=1, slug=step.slug, event_date=step.on, description=step.description,
            body=step.body, links=list(step.links), source=step.source,
        )
    elif isinstance(step, Document):
        source = temp / "inbox" / Path(step.path).name
        source.parent.mkdir(exist_ok=True)
        source.write_bytes(document_bytes(step))
        filed = Documents(brain, writer.reader).store(source, step.path, move=True)
        writer.write(
            type="document", version=1, slug=step.slug, event_date=step.on, description=step.description,
            body=step.contents, links=list(step.links), details=filed,
        )
    elif isinstance(step, Snapshot):
        writer.write(
            type="snapshot", version=1, slug=step.slug, event_date=step.on, description=step.description,
            body=step.body, links=list(step.links), details={"scope": step.scope},
        )
    elif isinstance(step, Revision):
        [(entry, _)] = writer.reader.holders([step.of])[step.of]
        writer.write(type=step.type, version=1, entry=entry, **step.fields)
    else:
        raise TypeError(f"not a step: {step!r}")


def document_bytes(document: Document) -> bytes:
    """A filed document's file: its contents, then its boilerplate."""
    text = document.contents + ("\n" + document.footer if document.footer else "")
    return text.encode("utf-8")


def ids(brain: Path = BRAIN) -> dict[str, str]:
    """Each entry's id, by the slug it was created under. A merge adds a slug
    to the entry kept, so the slug alone can name two entries."""
    found = {}
    for path in sorted((brain / "events").glob("*.jsonl")):
        for line in path.read_bytes().splitlines():
            record = json.loads(line)
            if record["entry"] == record["id"]:
                found[record["slugs"][0]] = record["id"]
    return found


def main() -> int:
    shutil.rmtree(BRAIN, ignore_errors=True)
    build(BRAIN)
    files = sorted(path for path in BRAIN.rglob("*") if path.is_file())
    print(f"wrote {len(files)} files to {BRAIN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
