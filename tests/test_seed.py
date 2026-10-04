import hashlib
import json
from pathlib import Path

import seed
from brain.read import Reader
from stories import STORIES, Document, Entity, Journal, Revision, Snapshot


def files_of(folder: Path) -> dict[str, bytes]:
    return {path.relative_to(folder).as_posix(): path.read_bytes() for path in sorted(folder.rglob("*")) if path.is_file()}


def records() -> list[dict]:
    return [json.loads(line) for path in sorted((seed.BRAIN / "events").glob("*.jsonl"))
            for line in path.read_bytes().splitlines()]


def test_a_fresh_build_matches_the_checked_in_brain_byte_for_byte(tmp_path):
    seed.build(tmp_path / "brain")
    assert files_of(tmp_path / "brain") == files_of(seed.BRAIN)


def test_every_step_of_the_stories_is_one_record(tmp_path):
    kinds = {Entity: "entity", Journal: "journal", Document: "document", Snapshot: "snapshot"}
    steps = [step for story in STORIES.values() for step in story]
    written = records()
    assert len(written) == len(steps) == len({record["id"] for record in written})
    originals = {record["slugs"][0]: record["type"] for record in written if record["entry"] == record["id"]}
    assert originals == {step.slug: kinds[type(step)] for step in steps if not isinstance(step, Revision)}
    assert sum(record["entry"] != record["id"] for record in written) == sum(isinstance(s, Revision) for s in steps)


def test_every_link_names_an_entry_and_the_merge_makes_one_set(tmp_path):
    reader = Reader(seed.BRAIN, tmp_path / "data")
    carried = {slug for record in records() for slug in record["slugs"]}
    assert {link for record in records() for link in record["links"]} <= carried
    [dragon] = [id for id, name in reader.holders(["the-dragon"])["the-dragon"] if name == "The dragon"]
    [kept] = reader.holders(["sir-fluffington"])["sir-fluffington"]
    assert reader.read([dragon])[0]["merged_into"] == kept[0]
    by_either = [{hit.id for hit in reader.search(slugs=[slug])} for slug in ("the-dragon", "sir-fluffington")]
    assert by_either[0] == by_either[1]
    assert "2026-06-28-dragon-curtain-fire" in {s for hit in reader.search(slugs=["sir-fluffington"]) for s in hit.slugs}


def test_every_filed_document_is_where_its_entry_says_with_the_hash_it_records(tmp_path):
    documents = {record["details"]["path"]: record["details"]["sha256"]
                 for record in records() if record["type"] == "document"}
    filed = files_of(seed.BRAIN / "documents")
    assert set(filed) == set(documents)
    for path, digest in documents.items():
        assert hashlib.sha256(filed[path]).hexdigest() == digest


def test_a_revision_reads_back_on_its_entry(tmp_path):
    reader = Reader(seed.BRAIN, tmp_path / "data")
    slug = "2026-06-01-hovercart-float-inspection"
    [inspection] = reader.read([reader.holders([slug])[slug][0][0]])
    assert "41,020" in inspection["description"]
    assert "41,200" in inspection["body"]
    assert "41,020" in inspection["amendments"][0]["body"]
