import datetime as dt
import json
import re
import uuid

import pytest

import brain.write
from brain.format import FIELDS, RecordError, file_created_at
from brain.write import Writer

from conftest import entry, event_files, lines_of, python, records_of

T0 = dt.datetime(2026, 9, 28, 23, 14, 32, tzinfo=dt.timezone.utc)


class Clock:
    def __init__(self, now: dt.datetime = T0):
        self.now = now

    def __call__(self) -> dt.datetime:
        return self.now


def test_an_entry_is_written_as_one_stamped_line_in_the_envelope(writer, store):
    details = {"odometer": 48210, "parts": ["oil", "filter"]}
    full_id = writer.write_entry(**entry(source="voice", details=details))
    bare_id = writer.write_entry(**entry())

    [path] = event_files(store)
    full, bare = records_of(path)
    assert list(full) == list(FIELDS)
    assert full["id"] == full_id and uuid.UUID(full_id).version == 7
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", full["recorded_at"])
    assert full["details"] == details
    # Every record has the same columns: details is always there, source only when given.
    assert bare["id"] == bare_id
    assert bare["details"] == {} and "source" not in bare


@pytest.mark.parametrize(
    "overrides",
    [{"description": " "}, {"body": chr(0xD800)}],
    ids=["blank description", "text that is not valid Unicode"],
)
def test_a_rejected_entry_writes_nothing(writer, store, overrides):
    with pytest.raises(RecordError):
        writer.write_entry(**entry(**overrides))
    assert event_files(store) == []


def test_a_torn_last_line_is_ended_before_the_next_append(writer, store):
    writer.write_entry(**entry(description="first"))
    [path] = event_files(store)
    with open(path, "ab") as file:
        file.write(b'{"id":"0199a8c4-torn","type":"jou')

    writer.write_entry(**entry(description="after"))

    first, torn, after = lines_of(path)
    assert torn == b'{"id":"0199a8c4-torn","type":"jou'
    assert json.loads(first)["description"] == "first"
    assert json.loads(after)["description"] == "after"


def test_a_file_that_reaches_the_line_limit_is_left_for_a_new_one(writer, store, monkeypatch):
    monkeypatch.setattr(brain.write, "ROLL_LINES", 3)
    for n in range(7):
        writer.write_entry(**entry(description=f"entry {n}"))

    assert sorted(len(records_of(f)) for f in event_files(store)) == [1, 3, 3]


def test_a_file_seven_days_old_is_left_for_a_new_one(store, state):
    clock = Clock()
    writer = Writer(store, state, clock=clock)
    writer.write_entry(**entry(description="day 0"))
    clock.now = T0 + dt.timedelta(days=6, hours=23)
    writer.write_entry(**entry(description="day 6"))
    clock.now = T0 + dt.timedelta(days=7)
    writer.write_entry(**entry(description="day 7"))

    old, new = event_files(store)
    assert [r["description"] for r in records_of(old)] == ["day 0", "day 6"]
    assert [r["description"] for r in records_of(new)] == ["day 7"]
    assert file_created_at(new.name) == clock.now


def test_a_machine_whose_file_is_gone_starts_a_new_one(writer, store):
    writer.write_entry(**entry())
    [path] = event_files(store)
    path.unlink()

    writer.write_entry(**entry(description="after"))

    [new] = event_files(store)
    assert new != path
    assert [r["description"] for r in records_of(new)] == ["after"]


def test_a_machine_whose_state_is_missing_starts_a_new_file(writer, store, state):
    writer.write_entry(**entry(description="before"))
    [path] = event_files(store)
    for file in state.glob("*.json"):
        file.unlink()

    writer.write_entry(**entry(description="after"))

    assert [r["description"] for r in records_of(path)] == ["before"]
    [new] = [f for f in event_files(store) if f != path]
    assert [r["description"] for r in records_of(new)] == ["after"]


def test_a_machine_never_appends_to_a_file_it_did_not_create(store, tmp_path):
    Writer(store, tmp_path / "machine a").write_entry(**entry(description="a"))
    Writer(store, tmp_path / "machine b").write_entry(**entry(description="b"))
    Writer(store, tmp_path / "machine a").write_entry(**entry(description="a again"))

    by_file = sorted([r["description"] for r in records_of(path)] for path in event_files(store))
    assert by_file == [["a", "a again"], ["b"]]


def test_two_brains_on_one_machine_keep_separate_state(tmp_path, state):
    first, second = tmp_path / "first", tmp_path / "second"
    Writer(first, state).write_entry(**entry(description="first"))
    Writer(second, state).write_entry(**entry(description="second"))
    Writer(first, state).write_entry(**entry(description="first again"))

    [path] = event_files(first)
    assert [r["description"] for r in records_of(path)] == ["first", "first again"]


WRITE_MANY = """
import sys
from brain.write import Writer
store, state, name, count = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
writer = Writer(store, state)
for n in range(count):
    writer.write_entry(type="journal", version=1, event_date="2026-09-14",
                       description=f"{name} {n}", body=name * 5000)
"""


def test_concurrent_sessions_append_whole_lines(store, state):
    sessions, count = 6, 25
    procs = [python(WRITE_MANY, str(store), str(state), f"s{i}", str(count)) for i in range(sessions)]
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
