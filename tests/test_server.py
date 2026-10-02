import asyncio
import json
import os
import subprocess
import sys

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession

from conftest import PLUGIN
from server.serve import build

TOOLS = {"write_journal", "revise_journal", "write_entity", "write_snapshot", "search", "read", "resolve", "store_document"}


@pytest.fixture
def server(brain_dir, data_dir):
    brain_dir.mkdir()
    return build(brain_dir, data_dir)


def calls(server, *steps):
    """Runs each (tool, arguments) in turn, in one session, and returns each
    result: the parsed JSON, or the error text of an error result."""

    async def run():
        results = []
        async with Client(server) as client:
            for name, arguments in steps:
                result = await client.call_tool(name, arguments)
                text = result.content[0].text
                results.append(("error", text) if result.is_error else json.loads(text))
        return results

    return asyncio.run(run())


def test_every_tool_is_listed_with_its_rules(server):
    async def run():
        async with Client(server) as client:
            return (await client.list_tools()).tools

    tools = {tool.name: tool for tool in asyncio.run(run())}
    assert set(tools) == TOOLS
    assert "triage" in tools["write_journal"].description
    assert tools["search"].annotations.read_only_hint is True
    assert tools["write_journal"].annotations.read_only_hint is False


def test_an_entry_about_an_entity_is_written_found_and_read(server):
    entity, journal, resolved, found, read = calls(
        server,
        ("write_entity", {"slug": "zorblax", "name": "Zorblax", "kind": "vehicle", "body": "The hover car.",
                          "aliases": ["the car"]}),
        ("write_journal", {"event_date": "2026-09-14", "description": "Oil change at 48k",
                           "body": "Oil and filter changed.", "entities": ["zorblax"]}),
        ("resolve", {"names": ["the car"]}),
        ("search", {"entities": ["zorblax"], "types": ["journal"]}),
        ("read", {"ids": []}),
    )

    assert resolved["matches"]["the car"][0]["slug"] == "zorblax"
    assert [hit["id"] for hit in found["hits"]] == [journal["id"]]
    assert found["hits"][0]["description"] == "Oil change at 48k"
    assert read == {"records": []}
    assert entity["id"] != journal["id"]


def test_a_revision_is_read_back_with_its_amendment(server):
    [journal] = calls(server, ("write_journal", {"event_date": "2026-09-14", "description": "Oil change",
                                                 "body": "Oil changed."}))
    revision, read = calls(
        server,
        ("revise_journal", {"entry": journal["id"], "description": "Oil change and tyre rotation",
                            "amendment": "The tyres were rotated too."}),
        ("read", {"ids": [journal["id"]]}),
    )

    [record] = read["records"]
    assert record["description"] == "Oil change and tyre rotation"
    assert record["body"] == "Oil changed."
    assert [a["body"] for a in record["amendments"]] == ["The tyres were rotated too."]
    assert revision["id"] != journal["id"]


def test_a_failure_the_model_can_fix_is_an_error_result_with_how(server):
    unknown, pattern, date = calls(
        server,
        ("write_journal", {"event_date": "2026-09-14", "description": "Oil change", "body": "Oil changed.",
                           "entities": ["nobody"]}),
        ("search", {"pattern": "-oil"}),
        ("search", {"event_date_from": "September"}),
    )

    assert unknown[0] == "error" and "nobody" in unknown[1] and "resolve or write it first" in unknown[1]
    assert pattern[0] == "error" and "a word to find" in pattern[1]
    assert date[0] == "error" and "YYYY-MM-DD" in date[1]


def test_a_search_past_the_ceiling_fails_with_ranges_to_search(server):
    steps = [("write_journal", {"event_date": f"2026-{month:02}-01", "description": f"Walk {n}",
                                "body": "A walk."}) for month in range(1, 13) for n in range(10)]
    *_, too_many = calls(server, *steps, ("search", {"pattern": "walk"}))

    assert too_many[0] == "error"
    assert "120 entries match" in too_many[1] and "2026-01-01 to" in too_many[1]


def test_a_document_is_filed_and_named_by_an_entry(server, brain_dir, tmp_path):
    scan = tmp_path / "scan.pdf"
    scan.write_bytes(b"%PDF invoice")
    filed, refused = calls(
        server,
        ("store_document", {"source": str(scan), "path": "car/invoice.pdf"}),
        ("store_document", {"source": str(scan), "path": "../invoice.pdf"}),
    )

    assert filed["path"] == "car/invoice.pdf" and len(filed["sha256"]) == 64
    assert (brain_dir / "documents" / "car" / "invoice.pdf").read_bytes() == b"%PDF invoice"
    assert refused[0] == "error" and "relative" in refused[1]


def test_the_server_answers_over_stdio_and_keeps_stdout_for_the_protocol(brain_dir, data_dir):
    brain_dir.mkdir()
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "server.serve"],
        env={"PYTHONPATH": str(PLUGIN), "BRAIN_DIR": str(brain_dir), "BRAIN_DATA_DIR": str(data_dir)},
    )

    async def run():
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            written = await session.call_tool("write_journal", {"event_date": "2026-09-14",
                                                                "description": "Oil change", "body": "Oil changed."})
            found = await session.call_tool("search", {"pattern": "oil"})
            return json.loads(written.content[0].text), json.loads(found.content[0].text)

    written, found = asyncio.run(run())
    assert [hit["id"] for hit in found["hits"]] == [written["id"]]


def test_a_server_with_no_brain_folder_exits_saying_so(tmp_path):
    env = os.environ | {"PYTHONPATH": str(PLUGIN), "BRAIN_DIR": "${user_config.brain_folder}",
                        "BRAIN_DATA_DIR": str(tmp_path / "data")}

    done = subprocess.run([sys.executable, "-m", "server.serve"], env=env, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=60)

    assert done.returncode == 1
    assert done.stdout == ""
    assert "BRAIN_DIR is not set" in done.stderr
