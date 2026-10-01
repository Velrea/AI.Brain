import datetime as dt

from brain.write import Writer

from conftest import entry, event_files, lines_of


def test_an_invalid_line_and_a_torn_last_line_are_skipped(writer, reader, store):
    writer.write_entry(**entry(description="before"))
    [path] = event_files(store)
    with open(path, "ab") as file:
        file.write(b'not json\n{"id":"0199a8c4-no-envelope"}\n')
    writer.write_entry(**entry(description="after"))
    with open(path, "ab") as file:
        file.write(b'{"id":"0199a8c4-torn","description":"caf\xc3')  # cut mid-character

    assert [hit.description for hit in reader.search().hits] == ["before", "after"]


def test_search_returns_lean_hits_a_page_at_a_time_in_event_date_order(
    writer, other_machine, reader
):
    writer.write_entry(**entry(event_date="2026-03-01", description="Tyres"))
    other_machine.write_entry(**entry(event_date="2026-01-01", description="Oil change"))
    writer.write_entry(**entry(event_date="2026-02-01", description="Brakes"))

    first = reader.search(limit=2)
    second = reader.search(limit=2, offset=2)

    # Records from two files interleave by what they say happened, not where they sit.
    assert [hit.description for hit in first.hits + second.hits] == ["Oil change", "Brakes", "Tyres"]
    assert first.total == second.total == reader.search(offset=5).total == 3
    oil = first.hits[0]
    assert (oil.type, oil.event_date, oil.snippet) == ("journal", "2026-01-01", "## Service Oil and filter changed.")


def test_a_pattern_matches_description_or_body_of_any_type_in_any_case(writer, reader):
    writer.write_entry(**entry(description="Started Zorblax", body="Two drops each morning."))
    writer.write_entry(**entry(
        type="snapshot", description="Current potions",
        body="## Current\n" + "Moonberry extract daily. " * 20 + "Zorblax two drops. " + "Glimmerol at night. " * 20,
    ))
    writer.write_entry(**entry(description="Oil change"))

    hits = reader.search("ZORBLAX|fizzlorin").hits

    assert [(hit.type, hit.description) for hit in hits] == [
        ("journal", "Started Zorblax"), ("snapshot", "Current potions"),
    ]
    # A long body is cut to a stretch around its first match.
    assert hits[1].snippet.startswith("…") and "Zorblax two drops." in hits[1].snippet
    assert len(hits[1].snippet) < 200


def test_search_filters_by_type_event_date_recorded_time_and_details(store, tmp_path, reader):
    now = [dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)]
    writer = Writer(store, tmp_path / "state", clock=lambda: now[0])
    writer.write_entry(**entry(event_date="2026-01-10", description="January"))
    writer.write_entry(**entry(event_date="2026-02-10", description="February"))
    writer.write_entry(**entry(type="snapshot", description="Snapshot", details={"scope": "car"}))
    now[0] = dt.datetime(2026, 9, 5, tzinfo=dt.timezone.utc)
    writer.write_entry(**entry(event_date="2026-03-10", description="Late"))

    def found(**filters):
        return [hit.description for hit in reader.search(**filters).hits]

    assert found(types=["snapshot"]) == ["Snapshot"]
    assert found(event_date_from="2026-02-01", event_date_to="2026-03-10") == ["February", "Late"]
    assert found(recorded_after="2026-09-03") == ["Late"]
    assert found(details={"scope": "car"}) == ["Snapshot"]


def test_read_returns_full_records_for_a_list_of_ids_in_one_call(writer, reader):
    oil = writer.write_entry(**entry(event_date="2026-01-10", source="voice", details={"odometer": 48210}))
    tyres = writer.write_entry(**entry(event_date="2026-03-01", description="Tyres", body="Four new."))

    first, second = reader.read([tyres, "0199a8c4-missing", oil])

    assert first == {
        "id": oil, "type": "journal", "version": 1, "recorded_at": first["recorded_at"],
        "event_date": "2026-01-10", "description": "Oil change", "source": "voice",
        "body": "## Service\nOil and filter changed.", "details": {"odometer": 48210},
    }
    assert (second["id"], second["source"], second["details"]) == (tyres, None, {})


def test_a_record_in_two_files_is_returned_once(writer, other_machine, reader, store):
    copied = writer.write_entry(**entry(description="Oil change"))
    other_machine.write_entry(**entry(description="Tyres", body="Four new tyres."))
    [line] = [line for path in event_files(store) for line in lines_of(path) if copied.encode() in line]
    [theirs] = [path for path in event_files(store) if line not in lines_of(path)]
    with open(theirs, "ab") as file:
        file.write(line + b"\n")

    assert [hit.id for hit in reader.search("oil").hits] == [copied]
    assert [record["id"] for record in reader.read([copied])] == [copied]
