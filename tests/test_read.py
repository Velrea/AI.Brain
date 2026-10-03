import datetime as dt

import pytest

import brain.read
from brain.read import TooManyHits
from brain.write import Writer

from conftest import create, entry, event_files, lines_of


def test_an_invalid_line_and_a_torn_last_line_are_skipped(writer, reader, brain_dir):
    writer.write_entry(**entry(description="before"))
    [path] = event_files(brain_dir)
    with open(path, "ab") as file:
        file.write(b'not json\n{"id":"0199a8c4-no-envelope"}\n')
    writer.write_entry(**entry(description="after"))
    with open(path, "ab") as file:
        file.write(b'{"id":"0199a8c4-torn","description":"caf\xc3')  # cut mid-character

    assert [hit.description for hit in reader.search()] == ["before", "after"]


def test_search_returns_every_lean_hit_in_event_date_order(writer, other_machine, reader):
    writer.write_entry(**entry(event_date="2026-03-01", description="Tyres"))
    other_machine.write_entry(**entry(event_date="2026-01-01", description="Oil change"))
    writer.write_entry(**entry(event_date="2026-02-01", description="Brakes"))

    hits = reader.search()

    # Records from two files interleave by what they say happened, not where they sit.
    assert [hit.description for hit in hits] == ["Oil change", "Brakes", "Tyres"]
    assert [hit.description for hit in reader.search(newest_first=True)] == ["Tyres", "Brakes", "Oil change"]
    oil = hits[0]
    assert (oil.type, oil.event_date, oil.snippet) == ("journal", "2026-01-01", "## Service Oil and filter changed.")


def test_a_search_finding_more_than_the_ceiling_fails_with_ranges_that_fit(
    writer, reader, monkeypatch
):
    monkeypatch.setattr(brain.read, "CEILING", 3)
    for day, count in (("2026-01-01", 2), ("2026-01-02", 1), ("2026-01-03", 2), ("2026-01-04", 4)):
        for n in range(count):
            writer.write_entry(**entry(event_date=day, description=f"{day} {n}"))

    with pytest.raises(TooManyHits) as refused:
        reader.search("oil")

    assert refused.value.total == 9
    # Each range fits the ceiling, except a single day no date range can split.
    assert refused.value.ranges == [
        ("2026-01-01", "2026-01-02", 3), ("2026-01-03", "2026-01-03", 2), ("2026-01-04", "2026-01-04", 4),
    ]
    assert "9 entries match" in str(refused.value)
    assert "2026-01-01 to 2026-01-02 (3)" in str(refused.value)
    assert len(reader.search("oil", event_date_to="2026-01-02")) == 3


def test_a_pattern_matches_description_or_body_of_any_type_in_any_case(writer, reader):
    writer.write_entry(**entry(description="Started Zorblax", body="Two drops each morning."))
    writer.write_entry(**entry(
        type="snapshot", description="Current potions",
        body="## Current\n" + "Moonberry extract daily. " * 20 + "Zorblax two drops. " + "Glimmerol at night. " * 20,
    ))
    writer.write_entry(**entry(description="Oil change"))

    hits = reader.search("ZORBLAX OR fizzlorin")

    assert [(hit.type, hit.description) for hit in hits] == [
        ("journal", "Started Zorblax"), ("snapshot", "Current potions"),
    ]
    # A long body is cut to a stretch around its first match.
    assert hits[1].snippet.startswith("…") and "Zorblax two drops." in hits[1].snippet
    assert len(hits[1].snippet) < 200


def test_search_filters_by_type_event_date_recorded_time_and_details(brain_dir, tmp_path, reader):
    now = [dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)]
    writer = Writer(brain_dir, tmp_path / "data", clock=lambda: now[0])
    writer.write_entry(**entry(event_date="2026-01-10", description="January"))
    writer.write_entry(**entry(event_date="2026-02-10", description="February"))
    writer.write_entry(**entry(type="snapshot", description="Snapshot", details={"scope": "car"}))
    now[0] = dt.datetime(2026, 9, 5, tzinfo=dt.timezone.utc)
    writer.write_entry(**entry(event_date="2026-03-10", description="Late"))

    def found(**filters):
        return [hit.description for hit in reader.search(**filters)]

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
        "body": "## Service\nOil and filter changed.", "slugs": first["slugs"], "aliases": [], "links": [],
        "details": {"odometer": 48210}, "amendments": [], "merged_into": None,
    }
    assert (second["id"], second["source"], second["details"]) == (tyres, None, {})


def test_a_record_in_two_files_is_returned_once(writer, other_machine, reader, brain_dir):
    copied = writer.write_entry(**entry(description="Oil change"))
    other_machine.write_entry(**entry(description="Tyres", body="Four new tyres."))
    [line] = [line for path in event_files(brain_dir) for line in lines_of(path) if copied.encode() in line]
    [theirs] = [path for path in event_files(brain_dir) if line not in lines_of(path)]
    with open(theirs, "ab") as file:
        file.write(line + b"\n")

    assert [hit.id for hit in reader.search("oil")] == [copied]
    assert [record["id"] for record in reader.read([copied])] == [copied]


def test_search_finds_entries_by_the_pattern_or_the_slugs_they_carry_or_link_to(writer, entries, reader):
    create(entries, "zorblax", type="entity", description="Zorblax", event_date="2026-05-01")
    create(entries, "started-zorblax", description="Started Zorblax", body="Two drops.", links=["zorblax"])
    # Linked, but never says the word: found only by its link. Written beneath
    # Entries.write, which would refuse dr-jekyll: a slug whose entry has not synced yet.
    writer.write_entry(**entry(event_date="2026-02-01", description="Doubled the dose", body="Four drops now.",
                               links=["zorblax", "dr-jekyll"]))
    # Says the word, but its links were missed: found only by its text.
    create(entries, "zorblax-refill", description="Zorblax refill", body="Collected.", event_date="2026-03-01")
    writer.write_entry(**entry(event_date="2026-04-01", description="Oil change", body="Done.", links=["car"]))
    # A journal entry links to another journal entry as readily as to an entity.
    create(entries, "follow-up", description="Follow-up", event_date="2026-04-02", links=["started-zorblax"])

    def found(pattern=None, **filters):
        return [hit.description for hit in reader.search(pattern, **filters)]

    assert found(slugs=["zorblax"]) == ["Started Zorblax", "Doubled the dose", "Zorblax"]
    assert found("zorblax", slugs=["zorblax"]) == [
        "Started Zorblax", "Doubled the dose", "Zorblax refill", "Zorblax",
    ]
    assert found(slugs=["dr-jekyll", "car"]) == ["Doubled the dose", "Oil change"]
    assert found(slugs=["started-zorblax"]) == ["Started Zorblax", "Follow-up"]
    assert found("zorblax", slugs=["zorblax"], types=["journal"], event_date_to="2026-02-28") == [
        "Started Zorblax", "Doubled the dose",
    ]
    assert found(slugs=[]) == []
    [hit] = reader.search(slugs=["zorblax"], types=["entity"])
    assert (hit.slugs, hit.names) == (["zorblax"], [])


def test_a_search_by_names_finds_the_likely_entries_of_its_types_and_says_which_name(entries, reader):
    create(entries, "dr-jekyll", type="entity", description="Dr. Jekyll", aliases=["Dr. J"])
    create(entries, "mr-hyde", type="entity", description="Mr. Hyde")
    create(entries, "zorblax", type="entity", description="Zorblax")
    create(entries, "moonberry-extract", type="entity", description="Moonberry extract")
    create(entries, "mom", type="entity", description="Mom")
    create(entries, "saw-dr-jekyll", description="Saw Dr. Jekyll")

    def found(*names, types=("entity",)):
        return {hit.slugs[0]: hit.names for hit in reader.search(names=list(names), types=list(types))}

    assert found("dr j") == {"dr-jekyll": ["dr j"]}  # by alias, in any case and punctuation
    assert found("Jekyll") == {"dr-jekyll": ["Jekyll"]}  # held whole as a word
    assert found("ZORBLAX", "zorblaxx") == {"zorblax": ["ZORBLAX", "zorblaxx"]}  # spelled alike
    assert found("moonberry") == {"moonberry-extract": ["moonberry"]}
    assert found("Tom", "glimmerol") == {}
    assert found("Jekyll", types=["entity", "journal"]) == {"dr-jekyll": ["Jekyll"], "saw-dr-jekyll": ["Jekyll"]}
    with pytest.raises(ValueError, match="needs types"):
        reader.search(names=["Jekyll"])


def test_a_search_by_names_keeps_to_five_for_each_name_best_first(entries, reader, monkeypatch):
    monkeypatch.setattr(brain.read, "MATCHES", 2)
    for slug in ("dr-jekyll", "dr-jekyll-senior", "dr-lanyon", "dr-who"):
        create(entries, slug, type="entity", description=slug.replace("-", " "))

    assert {hit.slugs[0] for hit in reader.search(names=["dr jekyll"], types=["entity"])} == {
        "dr-jekyll", "dr-jekyll-senior",
    }


def test_search_finds_the_document_entry_of_a_filed_document_by_its_hash(entries, reader):
    invoice, deed = "a" * 64, "b" * 64
    create(entries, "oil-change-invoice", type="document", details={"path": "car/invoice.pdf", "sha256": invoice})
    create(entries, "house-deed", type="document", details={"path": "house/deed.pdf", "sha256": deed})

    def found(**filters):
        return [hit.description for hit in reader.search(types=["document"], **filters)]

    assert found(details={"sha256": invoice}) == ["oil-change-invoice"]
    assert found(details={"path": "house/deed.pdf"}) == ["house-deed"]
    assert found(details={"sha256": "c" * 64}) == []


