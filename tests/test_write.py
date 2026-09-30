import datetime as dt
import json
import re
import uuid

import pytest

import brain.write
from brain.format import RecordError, file_created_at
from brain.write import Writer

from conftest import entry, event_files, lines_of, python, records_of

T0 = dt.datetime(2026, 9, 28, 23, 14, 32, tzinfo=dt.timezone.utc)


class Clock:
    def __init__(self, now: dt.datetime = T0):
        self.now = now

    def __call__(self) -> dt.datetime:
        return self.now


def test_an_append_writes_one_stamped_record_as_one_line(writer, store):
    record_id = writer.append(entry(source="voice"))

    [path] = event_files(store)
    [record] = records_of(path)
    assert record["id"] == record_id
    assert uuid.UUID(record_id).version == 7
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", record["recorded_at"])
    assert list(record) == [
        "id", "type", "version", "recorded_at", "event_date", "description", "source", "body",
    ]
    assert {k: record[k] for k in entry(source="voice")} == entry(source="voice")


def test_appends_go_to_the_same_file_until_it_rolls(writer, store):
    for n in range(5):
        writer.append(entry(description=f"entry {n}"))

    [path] = event_files(store)
    assert [r["description"] for r in records_of(path)] == [f"entry {n}" for n in range(5)]


def test_a_types_own_fields_are_written_after_the_common_ones(writer, store):
    writer.append(entry(type="vehicle_service", odometer=48210))

    [path] = event_files(store)
    [record] = records_of(path)
    assert record["odometer"] == 48210
    assert list(record)[-2:] == ["body", "odometer"]


def test_a_rejected_record_writes_nothing(writer, store):
    with pytest.raises(RecordError):
        writer.append(entry(id="mine"))
    with pytest.raises(RecordError):
        writer.append({"type": "journal"})
    assert event_files(store) == []


def test_a_torn_last_line_is_ended_before_the_next_append(writer, store):
    writer.append(entry(description="first"))
    [path] = event_files(store)
    with open(path, "ab") as file:
        file.write(b'{"id":"0199a8c4-torn","type":"jou')

    writer.append(entry(description="after"))

    lines = lines_of(path)
    assert lines[1] == b'{"id":"0199a8c4-torn","type":"jou'
    assert json.loads(lines[0])["description"] == "first"
    assert json.loads(lines[2])["description"] == "after"
    assert len(lines) == 3


def test_a_file_that_reaches_the_line_limit_is_left(writer, store, monkeypatch):
    monkeypatch.setattr(brain.write, "ROLL_LINES", 3)
    for n in range(7):
        writer.append(entry(description=f"entry {n}"))

    assert sorted(len(records_of(f)) for f in event_files(store)) == [1, 3, 3]


def test_a_file_seven_days_old_is_left(store, state):
    clock = Clock()
    writer = Writer(store, state, clock=clock)
    writer.append(entry(description="day 0"))
    clock.now = T0 + dt.timedelta(days=6, hours=23)
    writer.append(entry(description="day 6"))
    clock.now = T0 + dt.timedelta(days=7)
    writer.append(entry(description="day 7"))

    old, new = event_files(store)
    assert [r["description"] for r in records_of(old)] == ["day 0", "day 6"]
    assert [r["description"] for r in records_of(new)] == ["day 7"]
    assert file_created_at(new.name) == clock.now


def test_a_file_that_rolls_is_never_appended_to_again(writer, store, monkeypatch):
    monkeypatch.setattr(brain.write, "ROLL_LINES", 2)
    writer.append(entry())
    writer.append(entry())
    [sealed] = event_files(store)
    before = sealed.read_bytes()

    writer.append(entry())
    writer.append(entry())
    writer.append(entry())

    assert sealed.read_bytes() == before


def test_a_machine_whose_file_is_gone_starts_a_new_one(writer, store):
    writer.append(entry())
    [path] = event_files(store)
    path.unlink()

    writer.append(entry(description="after"))

    [new] = event_files(store)
    assert new != path
    assert [r["description"] for r in records_of(new)] == ["after"]


def test_a_machine_whose_state_is_missing_starts_a_new_file(writer, store, state):
    writer.append(entry(description="before"))
    [path] = event_files(store)
    for file in state.glob("*.json"):
        file.unlink()

    writer.append(entry(description="after"))

    assert [r["description"] for r in records_of(path)] == ["before"]
    [new] = [f for f in event_files(store) if f != path]
    assert [r["description"] for r in records_of(new)] == ["after"]


def test_a_machine_never_appends_to_a_file_it_did_not_create(store, tmp_path):
    Writer(store, tmp_path / "machine a").append(entry(description="a"))
    Writer(store, tmp_path / "machine b").append(entry(description="b"))
    Writer(store, tmp_path / "machine a").append(entry(description="a again"))

    by_writer = sorted(
        [r["description"] for r in records_of(path)] for path in event_files(store)
    )
    assert by_writer == [["a", "a again"], ["b"]]


def test_two_brains_on_one_machine_keep_separate_state(tmp_path, state):
    first, second = tmp_path / "first", tmp_path / "second"
    Writer(first, state).append(entry(description="first"))
    Writer(second, state).append(entry(description="second"))
    Writer(first, state).append(entry(description="first again"))

    [path] = event_files(first)
    assert [r["description"] for r in records_of(path)] == ["first", "first again"]
    assert len(list(state.glob("*.lock"))) == 2


APPEND_MANY = """
import sys
from brain.write import Writer
store, state, name, count = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
writer = Writer(store, state)
body = name * 5000
for n in range(count):
    writer.append({"type": "journal", "version": 1, "event_date": "2026-09-14",
                   "description": f"{name} {n}", "body": body})
"""


def test_concurrent_sessions_append_whole_lines(store, state):
    sessions, count = 6, 25
    procs = [python(APPEND_MANY, str(store), str(state), f"s{i}", str(count)) for i in range(sessions)]
    for proc in procs:
        _, err = proc.communicate(timeout=120)
        assert proc.returncode == 0, err

    [path] = event_files(store)
    records = records_of(path)
    assert len(records) == sessions * count
    for i in range(sessions):
        mine = [r["description"] for r in records if r["description"].startswith(f"s{i} ")]
        assert mine == [f"s{i} {n}" for n in range(count)]
    assert len({r["id"] for r in records}) == len(records)
