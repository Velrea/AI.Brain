import datetime as dt

import pytest

from brain.format import RecordError

from conftest import event_files, records_of


def test_a_journal_is_written_as_a_version_1_journal_with_no_details(entries, store):
    entry_id = entries.write_journal(
        event_date="2026-09-14", description="Oil change", body="Oil and filter changed."
    )

    [path] = event_files(store)
    [record] = records_of(path)
    assert record["id"] == entry_id
    assert (record["type"], record["version"], record["details"]) == ("journal", 1, {})


def test_a_snapshot_is_written_on_the_day_taken_with_its_scope(entries, store):
    entry_id = entries.write_snapshot(
        scope="current potions", description="Current potions", body="Zorblax, two drops."
    )
    with pytest.raises(RecordError):
        entries.write_snapshot(scope=" ", description="Blank scope", body="Nothing.")

    [path] = event_files(store)
    [record] = records_of(path)
    assert record["id"] == entry_id
    assert (record["type"], record["version"]) == ("snapshot", 1)
    assert record["event_date"] == dt.date.today().isoformat()
    assert record["details"] == {"scope": "current potions"}
