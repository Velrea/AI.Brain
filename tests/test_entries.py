from brain.entries import Entries

from conftest import event_files, records_of


def test_a_journal_is_written_as_a_version_1_journal_with_no_details(writer, store):
    entry_id = Entries(writer).write_journal(
        event_date="2026-09-14", description="Oil change", body="Oil and filter changed."
    )

    [path] = event_files(store)
    [record] = records_of(path)
    assert record["id"] == entry_id
    assert (record["type"], record["version"], record["details"]) == ("journal", 1, {})
