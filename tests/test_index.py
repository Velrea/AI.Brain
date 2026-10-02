import builtins
import datetime as dt
import shutil

import pytest

import brain.index
from brain.entries import Entries, UnknownEntities
from brain.format import RecordError, encode
from brain.read import PatternError, Reader
from brain.write import Writer

from conftest import entry, event_files, python, records_of


@pytest.fixture
def elsewhere(other_machine, store, tmp_path) -> Entries:
    """Another machine's entries, read through its own index."""
    return Entries(other_machine, Reader(store, tmp_path / "other machine state"))


def journal(entries: Entries, description: str = "Started Zorblax", **fields) -> str:
    return entries.write_journal(
        event_date=fields.pop("event_date", "2026-01-01"), description=description,
        body=fields.pop("body", "Two drops each morning."), **fields,
    )


def test_a_revision_replaces_metadata_and_keeps_the_body_with_its_amendment(entries, reader, store):
    entries.write_entity(slug="zorblax", name="Zorblax", kind="medication", body="A potion.")
    original = journal(entries, body="Two drops of Zorblax.")
    revision = entries.revise_journal(
        original, description="Started Zorblax tincture", event_date="2026-01-03",
        entities=["zorblax"], amendment="Correction: it was three drops, not two.",
    )

    [record] = reader.read([original])
    assert (record["id"], record["description"], record["event_date"]) == (
        original, "Started Zorblax tincture", "2026-01-03",
    )
    assert record["body"] == "Two drops of Zorblax."
    assert record["details"] == {"entities": ["zorblax"]}
    [amendment] = record["amendments"]
    assert (amendment["id"], amendment["body"]) == (revision, "Correction: it was three drops, not two.")
    # The revision's own id reads the entry it belongs to.
    assert reader.read([revision]) == [record]
    # Found by either text, or by the entities it now names, as one entry.
    assert [hit.id for hit in reader.search("three drops")] == [original]
    assert [hit.id for hit in reader.search("two drops")] == [original]
    assert [hit.id for hit in reader.search(entities=["zorblax"], types=["journal"])] == [original]
    assert reader.search("three drops")[0].snippet == "Correction: it was three drops, not two."
    # On disk: an original names itself, and a revision names the original.
    on_disk = {r["id"]: r for path in event_files(store) for r in records_of(path)}
    assert on_disk[original]["entry"] == original
    assert on_disk[revision]["entry"] == original
    assert on_disk[revision]["details"] == {"revises": ["description", "event_date", "entities"],
                                           "entities": ["zorblax"]}


def test_a_revision_of_metadata_alone_adds_no_amendment(entries, reader):
    original = journal(entries)
    entries.revise_journal(original, event_date="2026-01-02")

    [record] = reader.read([original])
    assert (record["description"], record["event_date"], record["amendments"]) == (
        "Started Zorblax", "2026-01-02", [],
    )


def test_a_revision_that_changes_nothing_or_names_no_journal_entry_is_refused(entries, store):
    original = journal(entries)
    snapshot = entries.write_snapshot(scope="potions", description="Potions", body="Zorblax.")
    before = sum(len(records_of(path)) for path in event_files(store))

    with pytest.raises(RecordError, match="must change"):
        entries.revise_journal(original)
    with pytest.raises(RecordError, match="non-empty"):
        entries.revise_journal(original, amendment=" ")
    with pytest.raises(RecordError, match="no journal entry"):
        entries.revise_journal(snapshot, description="Not a journal")
    with pytest.raises(RecordError, match="no journal entry"):
        entries.revise_journal("0199a8c4-0000-7000-8000-000000000000", description="Missing")
    with pytest.raises(UnknownEntities):
        entries.revise_journal(original, entities=["glimmerol"])
    assert sum(len(records_of(path)) for path in event_files(store)) == before


def test_a_revision_arriving_late_is_applied_on_the_next_read(entries, elsewhere, reader):
    original = journal(entries)
    assert [hit.description for hit in reader.search()] == ["Started Zorblax"]

    elsewhere.revise_journal(original, description="Started Zorblax, late")

    assert [hit.description for hit in reader.search()] == ["Started Zorblax, late"]


def test_a_revision_arriving_before_its_original_waits_for_it(entries, elsewhere, reader, store, tmp_path):
    original = journal(entries)
    elsewhere.revise_journal(original, description="Revised", amendment="Three drops.")
    [ours] = [path for path in event_files(store) if original in path.read_text("utf-8")
              and '"revises"' not in path.read_text("utf-8")]
    held = tmp_path / "held back"
    shutil.move(ours, held)

    # Only the revision has synced here, so there is no entry yet.
    assert reader.search() == [] and reader.read([original]) == []
    assert reader.search("three") == []

    shutil.move(held, ours)
    [record] = reader.read([original])
    assert (record["description"], [a["body"] for a in record["amendments"]]) == ("Revised", ["Three drops."])


def test_two_machines_revising_different_fields_both_hold(store, state, tmp_path, reader):
    # Two machines' ids order only by time, so each write takes a later millisecond.
    ticks = iter(dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc) + dt.timedelta(seconds=n) for n in range(9))
    entries = Entries(Writer(store, state, clock=lambda: next(ticks)), reader)
    elsewhere = Entries(
        Writer(store, tmp_path / "other machine state", clock=lambda: next(ticks)),
        Reader(store, tmp_path / "other machine state"),
    )
    original = journal(entries)
    entries.revise_journal(original, description="Ours")
    elsewhere.revise_journal(original, event_date="2026-02-02", amendment="Theirs.")
    # The newest revision of a field wins.
    entries.revise_journal(original, amendment="Ours again.")

    [record] = reader.read([original])
    assert (record["description"], record["event_date"]) == ("Ours", "2026-02-02")
    assert [a["body"] for a in record["amendments"]] == ["Theirs.", "Ours again."]

    entries.revise_journal(original, description="Ours, newest")
    assert reader.read([original])[0]["description"] == "Ours, newest"


def test_recorded_after_finds_an_entry_revised_since(store, state, tmp_path):
    now = [dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)]
    reader = Reader(store, state)
    entries = Entries(Writer(store, state, clock=lambda: now[0]), reader)
    original = journal(entries)
    journal(entries, "Untouched")
    now[0] = dt.datetime(2026, 9, 5, tzinfo=dt.timezone.utc)
    entries.revise_journal(original, amendment="Stopped it.")

    assert [hit.id for hit in reader.search(recorded_after="2026-09-03")] == [original]


def test_a_complete_line_is_taken_in_only_once_its_newline_arrives(writer, reader, store):
    writer.write_entry(**entry(description="before"))
    [path] = event_files(store)
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


def test_a_file_that_vanishes_rebuilds_the_index(writer, other_machine, reader, store):
    writer.write_entry(**entry(description="ours"))
    other_machine.write_entry(**entry(description="theirs"))
    assert len(reader.search()) == 2

    [theirs] = [path for path in event_files(store) if b"theirs" in path.read_bytes()]
    theirs.unlink()

    assert [hit.description for hit in reader.search()] == ["ours"]


def test_a_corrupt_index_is_rebuilt(writer, reader):
    writer.write_entry(**entry(description="kept"))
    reader.search()
    reader.index.path.write_bytes(b"not a database" * 1000)
    for suffix in ("-wal", "-shm"):
        (reader.index.path.parent / (reader.index.path.name + suffix)).unlink(missing_ok=True)

    assert [hit.description for hit in reader.search()] == ["kept"]


def test_an_index_caught_up_file_by_file_answers_as_one_rebuilt(entries, elsewhere, reader, store, tmp_path):
    entries.write_entity(slug="zorblax", name="Zorblax", kind="potion", aliases=["ZB"], body="A potion.")
    first = journal(entries, entities=["zorblax"])
    reader.search()
    elsewhere.write_entity(slug="zorblax", name="Zorblax", kind="potion", aliases=["green"], body="Green.")
    second = journal(elsewhere, "Doubled the dose", event_date="2026-02-01")
    reader.search()
    entries.revise_journal(second, entities=["zorblax"], amendment="Four drops.")
    elsewhere.revise_journal(first, description="Began Zorblax")

    rebuilt = Reader(store, tmp_path / "fresh state")
    for search in (dict(), dict(pattern="drops"), dict(entities=["zorblax"])):
        assert reader.search(**search) == rebuilt.search(**search)
    assert reader.read([first, second]) == rebuilt.read([first, second])
    assert reader.resolve(["zb", "green"]) == rebuilt.resolve(["zb", "green"])


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


def test_a_crash_midway_through_catching_up_loses_nothing(writer, other_machine, reader, store, state):
    writer.write_entry(**entry(description="ours"))
    other_machine.write_entry(**entry(description="theirs"))

    crashed = python(CRASH_MIDWAY, str(store), str(state))
    crashed.communicate(timeout=60)
    assert crashed.returncode == 3

    assert sorted(hit.description for hit in reader.search()) == ["ours", "theirs"]


SESSION = """
import sys
from brain.entries import Entries
from brain.read import Reader
from brain.write import Writer
store, state, name, count = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
reader = Reader(store, state)
entries = Entries(Writer(store, state), reader)
for n in range(count):
    id = entries.write_journal(event_date="2026-09-14", description=f"{name} {n}", body="Zorblax.")
    assert [r["id"] for r in reader.read([id])] == [id]
    if n % 3 == 0:
        entries.revise_journal(id, amendment=f"{name} {n} amended.")
    assert len(reader.search(f'"{name} {n}"')) >= 1
"""


def test_several_sessions_read_and_write_at_once(store, state, reader):
    sessions, count = 4, 15
    procs = [python(SESSION, str(store), str(state), f"s{i}", str(count)) for i in range(sessions)]
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


def test_an_entity_restated_is_one_hit_and_any_statement_reads_it(entries, reader):
    first = entries.write_entity(slug="zorblax", name="Zorblax", kind="potion", body="A potion.")
    newest = entries.write_entity(slug="zorblax", name="Zorblax tincture", kind="medication", body="Blue.")

    [hit] = reader.search(entities=["zorblax"])
    assert (hit.id, hit.description) == (newest, "Zorblax tincture")
    [record] = reader.read([first])
    assert (record["id"], record["body"], record["details"]["kind"]) == (newest, "Blue.", "medication")
