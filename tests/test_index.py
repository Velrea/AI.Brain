import builtins
import datetime as dt
import shutil

import pytest

import brain.index
from brain.entries import Entries
from brain.format import encode
from brain.read import PatternError, Reader
from brain.write import Writer

from conftest import create, entry, event_files, python, records_of


@pytest.fixture
def elsewhere(other_machine, brain_dir, tmp_path) -> Entries:
    """Another machine's entries, read through its own index."""
    return Entries(other_machine, Reader(brain_dir, tmp_path / "other machine data"))


def ticking(brain_dir, data_dir, tmp_path, reader) -> tuple[Entries, Entries]:
    """Two machines whose every write takes a later second, since their ids order only by time."""
    ticks = iter(dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc) + dt.timedelta(seconds=n) for n in range(99))
    ours = Entries(Writer(brain_dir, data_dir, clock=lambda: next(ticks)), reader)
    theirs = Entries(
        Writer(brain_dir, tmp_path / "other machine data", clock=lambda: next(ticks)),
        Reader(brain_dir, tmp_path / "other machine data"),
    )
    return ours, theirs


def revise(entries: Entries, entry_id: str, **fields) -> str:
    return entries.write(type=fields.pop("type", "journal"), version=1, entry=entry_id, **fields)


def test_a_revision_is_one_entry_found_by_either_text_and_its_new_links(entries, reader, brain_dir):
    create(entries, "zorblax", type="entity")
    original = create(entries, "started-zorblax", body="Two drops of Zorblax.")
    revision = revise(entries, original, links=["zorblax"], body="Correction: it was three drops, not two.")

    [record] = reader.read([original])
    # The revision's own id reads the entry it belongs to.
    assert reader.read([revision]) == [record]
    assert [hit.id for hit in reader.search("three drops")] == [original]
    assert [hit.id for hit in reader.search("two drops")] == [original]
    assert [hit.id for hit in reader.search(slugs=["zorblax"], types=["journal"])] == [original]
    assert reader.search("three drops")[0].snippet == "Correction: it was three drops, not two."


def test_a_revision_of_fields_alone_adds_no_amendment(entries, reader):
    original = create(entries, "started-zorblax", description="Started Zorblax")
    revise(entries, original, event_date="2026-01-02")

    [record] = reader.read([original])
    assert (record["description"], record["event_date"], record["amendments"]) == (
        "Started Zorblax", "2026-01-02", [],
    )


def test_a_revision_arriving_late_is_applied_on_the_next_read(entries, elsewhere, reader):
    original = create(entries, "started-zorblax", description="Started Zorblax")
    assert [hit.description for hit in reader.search()] == ["Started Zorblax"]

    revise(elsewhere, original, description="Started Zorblax, late")

    assert [hit.description for hit in reader.search()] == ["Started Zorblax, late"]


def test_a_revision_arriving_before_its_original_waits_for_it(entries, elsewhere, reader, brain_dir, tmp_path):
    original = create(entries, "started-zorblax")
    revise(elsewhere, original, description="Revised", body="Three drops.")
    [ours] = [path for path in event_files(brain_dir) if '"revises":[]' in path.read_text("utf-8")]
    held = tmp_path / "held back"
    shutil.move(ours, held)

    # Only the revision has synced here, so there is no entry yet.
    assert reader.search() == [] and reader.read([original]) == []
    assert reader.search("three") == []

    shutil.move(held, ours)
    [record] = reader.read([original])
    assert (record["description"], [a["body"] for a in record["amendments"]]) == ("Revised", ["Three drops."])


def test_two_machines_revising_different_fields_and_adding_names_both_hold(brain_dir, data_dir, tmp_path, reader):
    entries, elsewhere = ticking(brain_dir, data_dir, tmp_path, reader)
    original = create(entries, "zorblax", type="entity", details={"kind": "potion"})
    revise(entries, original, type="entity", description="Ours", aliases=["ZB"])
    revise(elsewhere, original, type="entity", event_date="2026-02-02", aliases=["the green drops"],
           details={"kind": "medication"}, body="Theirs.")
    # The newest revision of a field wins.
    revise(entries, original, type="entity", body="Ours again.")

    [record] = reader.read([original])
    assert (record["description"], record["event_date"], record["details"]) == (
        "Ours", "2026-02-02", {"kind": "medication"},
    )
    assert record["aliases"] == ["ZB", "the green drops"]
    assert [a["body"] for a in record["amendments"]] == ["Theirs.", "Ours again."]

    revise(entries, original, type="entity", description="Ours, newest")
    assert reader.read([original])[0]["description"] == "Ours, newest"


def test_recorded_after_finds_an_entry_revised_since(brain_dir, data_dir, tmp_path):
    now = [dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)]
    reader = Reader(brain_dir, data_dir)
    entries = Entries(Writer(brain_dir, data_dir, clock=lambda: now[0]), reader)
    original = create(entries, "started-zorblax")
    create(entries, "untouched")
    now[0] = dt.datetime(2026, 9, 5, tzinfo=dt.timezone.utc)
    revise(entries, original, body="Stopped it.")

    assert [hit.id for hit in reader.search(recorded_after="2026-09-03")] == [original]


def test_a_merge_makes_one_entry_of_two_and_one_set_of_what_links_to_either(entries, elsewhere, reader):
    kept = create(entries, "medication", type="entity", description="Medication")
    merged = create(entries, "meds", type="entity", description="Meds", body="Pills.")
    create(entries, "started-zorblax", links=["meds"], event_date="2026-01-02")
    create(entries, "refill", links=["medication"], event_date="2026-01-03")

    revise(entries, kept, type="entity", slug="meds")
    # An entry linking to the old slug that syncs in after the merge is covered too.
    create(elsewhere, "doubled-it", links=["meds"], event_date="2026-01-04")

    for slug in ("meds", "medication"):
        assert [hit.description for hit in reader.search(slugs=[slug])] == [
            "Medication", "started-zorblax", "refill", "doubled-it",
        ]
    # The entry merged away is a hit for nothing, and reads as merged into the one kept.
    assert reader.search("pills") == []
    [record] = reader.read([merged])
    assert record["merged_into"] == kept
    assert reader.read([kept])[0]["slugs"] == ["medication", "meds"]


def test_a_merge_arriving_before_the_entry_it_merges_settles_the_same(entries, elsewhere, reader, brain_dir, tmp_path):
    kept = create(entries, "medication", type="entity")
    merged = create(elsewhere, "meds", type="entity")
    create(elsewhere, "started-zorblax", links=["meds"], event_date="2026-01-02")
    revise(entries, kept, type="entity", slug="meds")
    [theirs] = [path for path in event_files(brain_dir) if b"started-zorblax" in path.read_bytes()]
    held = tmp_path / "held back"
    shutil.move(theirs, held)
    assert reader.read([kept])[0]["slugs"] == ["medication", "meds"]

    shutil.move(held, theirs)

    assert reader.read([merged])[0]["merged_into"] == kept
    assert [hit.description for hit in reader.search(slugs=["medication"])] == ["medication", "started-zorblax"]


def test_two_machines_creating_one_slug_keep_both_entries(entries, other_machine, reader):
    ours = create(entries, "dr-jekyll", type="entity", description="Dr. Jekyll")
    # Written beneath Entries.write, as a machine that had not yet synced ours would.
    theirs = other_machine.write_entry(**entry(type="entity", slugs=["dr-jekyll"],
                                               description="Dr. Jekyll, the physician"))
    linked = create(entries, "checkup", links=["dr-jekyll"])

    assert {hit.id for hit in reader.search(slugs=["dr-jekyll"])} == {ours, theirs, linked}
    assert [record["merged_into"] for record in reader.read([ours, theirs])] == [None, None]


def test_a_complete_line_is_taken_in_only_once_its_newline_arrives(writer, reader, brain_dir):
    writer.write_entry(**entry(description="before"))
    [path] = event_files(brain_dir)
    halfway = "0199a8c4-0000-7000-8000-000000000001"
    line = encode(entry(id=halfway, entry=halfway, recorded_at="2026-09-15T00:00:00Z", event_date="2026-09-15",
                       description="halfway"))
    with open(path, "ab") as file:
        file.write(line[:-1])  # Whole JSON, but not yet ended.

    assert [hit.description for hit in reader.search()] == ["before"]

    with open(path, "ab") as file:
        file.write(b"\n")
    assert [hit.description for hit in reader.search()] == ["before", "halfway"]


def test_a_read_with_nothing_new_opens_no_file(writer, other_machine, reader, monkeypatch):
    writer.write_entry(**entry(description="ours"))
    other_machine.write_entry(**entry(description="theirs"))
    reader.search()
    opened = []
    real_open = builtins.open
    monkeypatch.setattr(brain.index, "open", lambda path, *a, **k: opened.append(path) or real_open(path, *a, **k),
                        raising=False)

    reader.search()
    assert opened == []

    writer.write_entry(**entry(description="ours again"))
    reader.search()
    assert [path.name for path in opened] == [writer._load_state()["file"]]


def test_a_file_that_vanishes_rebuilds_the_index(writer, other_machine, reader, brain_dir):
    writer.write_entry(**entry(description="ours"))
    other_machine.write_entry(**entry(description="theirs"))
    assert len(reader.search()) == 2

    [theirs] = [path for path in event_files(brain_dir) if b"theirs" in path.read_bytes()]
    theirs.unlink()

    assert [hit.description for hit in reader.search()] == ["ours"]


def test_a_corrupt_index_is_rebuilt(writer, reader):
    writer.write_entry(**entry(description="kept"))
    reader.search()
    reader.index.path.write_bytes(b"not a database" * 1000)
    for suffix in ("-wal", "-shm"):
        (reader.index.path.parent / (reader.index.path.name + suffix)).unlink(missing_ok=True)

    assert [hit.description for hit in reader.search()] == ["kept"]


def test_an_index_caught_up_file_by_file_answers_as_one_rebuilt(entries, elsewhere, reader, brain_dir, tmp_path):
    zorblax = create(entries, "zorblax", type="entity", aliases=["ZB"])
    first = create(entries, "started-zorblax", links=["zorblax"])
    reader.search()
    revise(elsewhere, zorblax, type="entity", aliases=["green"])
    second = create(elsewhere, "doubled-the-dose", event_date="2026-02-01")
    meds = create(elsewhere, "meds", type="entity")
    reader.search()
    revise(entries, second, links=["zorblax", "meds"], body="Four drops.")
    revise(elsewhere, first, description="Began Zorblax")
    revise(entries, zorblax, type="entity", slug="meds")

    rebuilt = Reader(brain_dir, tmp_path / "fresh data")
    searches = (dict(), dict(pattern="drops"), dict(slugs=["zorblax"]), dict(slugs=["meds"]),
                dict(names=["zb", "green"], types=["entity"]))
    for search in searches:
        assert reader.search(**search) == rebuilt.search(**search)
    assert reader.read([first, second, zorblax, meds]) == rebuilt.read([first, second, zorblax, meds])


CRASH_MIDWAY = """
import os, sys
import brain.index
from brain.read import Reader
real = brain.index._add
calls = []
def add(con, records):
    calls.append(1)
    if len(calls) == 2:
        os._exit(3)  # Dies holding the second file's transaction.
    real(con, records)
brain.index._add = add
Reader(sys.argv[1], sys.argv[2]).search()
"""


def test_a_crash_midway_through_catching_up_loses_nothing(writer, other_machine, reader, brain_dir, data_dir):
    writer.write_entry(**entry(description="ours"))
    other_machine.write_entry(**entry(description="theirs"))

    crashed = python(CRASH_MIDWAY, str(brain_dir), str(data_dir))
    crashed.communicate(timeout=60)
    assert crashed.returncode == 3

    assert sorted(hit.description for hit in reader.search()) == ["ours", "theirs"]


SESSION = """
import sys
from brain.entries import Entries
from brain.read import Reader
from brain.write import Writer
brain_dir, data_dir, name, count = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
reader = Reader(brain_dir, data_dir)
entries = Entries(Writer(brain_dir, data_dir), reader)
for n in range(count):
    id = entries.write(type="journal", version=1, slug=f"{name}-{n}", event_date="2026-09-14",
                       description=f"{name} {n}", body="Zorblax.")
    assert [r["id"] for r in reader.read([id])] == [id]
    if n % 3 == 0:
        entries.write(type="journal", version=1, entry=id, body=f"{name} {n} amended.")
    assert len(reader.search(f'"{name} {n}"')) >= 1
"""


def test_several_sessions_read_and_write_at_once(brain_dir, data_dir, reader):
    sessions, count = 4, 15
    procs = [python(SESSION, str(brain_dir), str(data_dir), f"s{i}", str(count)) for i in range(sessions)]
    for proc in procs:
        _, err = proc.communicate(timeout=180)
        assert proc.returncode == 0, err

    assert len(reader.search("zorblax")) == sessions * count
    assert len(reader.search("amended")) == sessions * len(range(0, count, 3))


def test_a_pattern_finds_words_phrases_prefixes_and_either_side_of_or(writer, reader):
    writer.write_entry(**entry(description="Saw Dr. Jekyll", body="Two drops of Moonberry extract."))
    writer.write_entry(**entry(description="Oil change", body="Dr. Lanyon's garage, drop-off at nine."))
    writer.write_entry(**entry(description="Café visit", body="Extract of moonberry tea."))

    def found(pattern):
        return [hit.description for hit in reader.search(pattern)]

    assert found("drop") == ["Saw Dr. Jekyll", "Oil change"]  # any form of the word
    assert found('"moonberry extract"') == ["Saw Dr. Jekyll"]  # a phrase as written
    assert found("moonberry extract") == ["Saw Dr. Jekyll", "Café visit"]  # every word, anywhere
    assert found("moonb*") == ["Saw Dr. Jekyll", "Café visit"]
    assert found("moonberry -tea") == ["Saw Dr. Jekyll"]
    assert found("jekyll OR lanyon") == ["Saw Dr. Jekyll", "Oil change"]
    assert found("Dr. J*") == ["Saw Dr. Jekyll"]  # punctuation is no syntax
    assert found("drop-off") == ["Oil change"]
    assert found("cafe") == ["Café visit"]  # accents read as plain letters
    for pattern in ("", " - ", "-tea", "OR"):
        with pytest.raises(PatternError):
            reader.search(pattern)
