import json
import re
from pathlib import Path

import pytest

from conftest import PLUGIN

ROOT = PLUGIN.parent
SPEC = "https://agent-plugins.org/schemas/1.0.0/"
SKILL_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
"""The frontmatter fields the Agent Skills specification defines."""


def load(path: Path) -> dict:
    return json.loads(path.read_text("utf-8"))


def test_every_manifest_names_the_plugin_brain_and_no_setting():
    portable, claude = load(PLUGIN / "plugin.json"), load(PLUGIN / ".claude-plugin" / "plugin.json")

    assert portable["$schema"] == SPEC + "plugin.schema.json"
    assert portable["name"] == claude["name"] == "brain"
    assert re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", portable["name"])
    for manifest in (portable, claude):
        assert "userConfig" not in manifest and "hooks" not in manifest
    assert not (PLUGIN / "hooks").exists()


def test_every_server_config_starts_the_same_launcher_and_sets_nothing_an_install_chooses():
    portable, claude = load(PLUGIN / "mcp.json"), load(PLUGIN / ".mcp.json")

    assert set(portable) == {"$schema", "mcpServers"} and portable["$schema"] == SPEC + "mcp.schema.json"
    assert portable["mcpServers"] == {"brain": {"type": "stdio", "command": "./scripts/brain"}}
    [server] = claude["mcpServers"].values()
    assert server["command"] == "${CLAUDE_PLUGIN_ROOT}/scripts/brain"
    # Only the host's data folder, under the name the code reads.
    assert server.get("env", {}) == {"PLUGIN_DATA": "${CLAUDE_PLUGIN_DATA}"}
    assert (PLUGIN / "scripts" / "brain").is_file() and (PLUGIN / "scripts" / "brain.cmd").is_file()


@pytest.mark.parametrize("marketplace", [
    ".claude-plugin/marketplace.json", ".cursor-plugin/marketplace.json", ".agents/plugins/marketplace.json",
])
def test_every_marketplace_lists_the_plugin_from_its_folder(marketplace):
    [entry] = load(ROOT / marketplace)["plugins"]
    source = entry["source"]
    assert entry["name"] == "brain"
    assert (source if isinstance(source, str) else source["path"]) == "./plugin"


@pytest.mark.parametrize("skill", sorted(PLUGIN.glob("skills/*/SKILL.md")), ids=lambda path: path.parent.name)
def test_every_skill_keeps_to_the_agent_skills_fields_and_names_no_host_variable(skill):
    head, body = skill.read_text("utf-8").removeprefix("---\n").split("\n---\n", 1)
    fields = dict(line.split(": ", 1) for line in head.splitlines())

    assert set(fields) <= SKILL_FIELDS
    assert fields["name"] == skill.parent.name
    assert 0 < len(json.loads(fields["description"])) <= 1024
    assert "${" not in body
