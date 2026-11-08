import json
import sys

import pytest

from server.folders import (
    PLUGIN, SETTINGS, BrainMissing, FolderError, brain_setting, configure, data_dir, existing, host_path,
)


def claude_settings(folder, configs) -> dict:
    """An environment as Claude Code starts the server in, with its own settings in `folder`."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "settings.json").write_text(json.dumps({"theme": "dark", "pluginConfigs": configs}), "utf-8")
    return {"CLAUDE_PLUGIN_ROOT": str(PLUGIN), "CLAUDE_CONFIG_DIR": str(folder)}


def test_brain_dir_overrides_the_settings(tmp_path):
    (tmp_path / "brain").mkdir()
    configure(tmp_path / "data", str(tmp_path / "brain"), environ={})
    assert brain_setting(tmp_path / "data", {"BRAIN_DIR": str(tmp_path / "other")}) == (tmp_path / "other", "from BRAIN_DIR")


@pytest.mark.parametrize("value", [None, "", "  ", "${user_config.brain_folder}"])
def test_with_no_brain_dir_and_no_settings_the_brain_is_not_configured(tmp_path, value):
    environ = {} if value is None else {"BRAIN_DIR": value}
    assert brain_setting(tmp_path / "data", environ) == (None, "not configured")


def test_configure_keeps_the_folder_in_the_data_folders_settings(tmp_path):
    data, brain = tmp_path / "data", tmp_path / "brain"
    brain.mkdir()

    assert configure(data, str(brain), environ={}) == brain.resolve()
    assert brain_setting(data, {}) == (brain.resolve(), f"from {SETTINGS}")
    assert json.loads((data / SETTINGS).read_text("utf-8")) == {"brain_folder": str(brain.resolve())}


def test_configure_again_changes_the_folder(tmp_path):
    data, first, second = tmp_path / "data", tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    configure(data, str(first), environ={})

    configure(data, str(second), environ={})
    assert brain_setting(data, {})[0] == second.resolve()


def test_a_folder_that_does_not_exist_is_refused_unless_created(tmp_path):
    data, missing = tmp_path / "data", tmp_path / "unmounted drive" / "Brain"

    with pytest.raises(BrainMissing, match="does not exist") as refused:
        configure(data, str(missing), environ={})
    assert refused.value.path == missing
    assert not missing.exists() and not (data / SETTINGS).exists()

    assert configure(data, str(missing), create=True, environ={}) == missing.resolve()
    assert missing.is_dir()


def test_a_configured_folder_that_is_gone_is_reported_not_created(tmp_path):
    data, brain = tmp_path / "data", tmp_path / "brain"
    brain.mkdir()
    configure(data, str(brain), environ={})
    brain.rmdir()

    path, _ = brain_setting(data, {})
    with pytest.raises(BrainMissing):
        existing(path)
    assert not brain.exists()


def test_configure_refuses_a_relative_path_a_set_brain_dir_and_a_data_folder_inside_the_brain(tmp_path):
    brain = tmp_path / "brain"
    brain.mkdir()
    with pytest.raises(FolderError, match="not an absolute path"):
        configure(tmp_path / "data", "brain", environ={})
    with pytest.raises(FolderError, match="overrides"):
        configure(tmp_path / "data", str(brain), environ={"BRAIN_DIR": str(brain)})
    with pytest.raises(FolderError, match="inside the Brain folder"):
        configure(brain / "data", str(brain), environ={})
    assert not (brain / "data" / SETTINGS).exists()


@pytest.mark.parametrize("text", ["{not json", '{"brain_folder": 7}', '{"brain_folder": "relative"}', "[]"])
def test_settings_that_cannot_be_read_are_reported(tmp_path, text):
    (tmp_path / SETTINGS).write_text(text, "utf-8")
    with pytest.raises(FolderError, match="configure the Brain folder again"):
        brain_setting(tmp_path, {})


def test_a_claude_install_carries_its_folder_over_from_claudes_settings(tmp_path):
    data = tmp_path / "data"
    claude = tmp_path / ".claude"
    environ = claude_settings(claude, {"brain@ai-brain": {"options": {"brain_folder": str(tmp_path / "Brain")}},
                                       "other@ai-brain": {"options": {"brain_folder": str(tmp_path / "Other")}}})
    before = (claude / "settings.json").read_bytes()

    assert brain_setting(data, environ) == (tmp_path / "Brain", "carried over from Claude Code's settings")
    assert brain_setting(data, {}) == (tmp_path / "Brain", f"from {SETTINGS}")
    assert (claude / "settings.json").read_bytes() == before


@pytest.mark.parametrize("configs", [
    {},
    {"brain@ai-brain": {"options": {}}},
    {"brain@ai-brain": {"options": {"brain_folder": "${user_config.brain_folder}"}}},
    {"brain@ai-brain": {"options": {"brain_folder": "relative/Brain"}}},
    {"brain@one": {"options": {"brain_folder": "TMP/one"}}, "brain@two": {"options": {"brain_folder": "TMP/two"}}},
])
def test_no_folder_or_several_that_differ_in_claudes_settings_carry_nothing_over(tmp_path, configs):
    configs = json.loads(json.dumps(configs).replace("TMP", tmp_path.as_posix()))
    environ = claude_settings(tmp_path / ".claude", configs)
    assert brain_setting(tmp_path / "data", environ) == (None, "not configured")
    assert not (tmp_path / "data" / SETTINGS).exists()


def test_claudes_settings_are_read_only_when_claude_started_the_server(tmp_path):
    environ = claude_settings(tmp_path / ".claude", {"brain@ai-brain": {"options": {"brain_folder": str(tmp_path)}}})
    del environ["CLAUDE_PLUGIN_ROOT"]
    assert brain_setting(tmp_path / "data", environ) == (None, "not configured")
    environ["CLAUDE_PLUGIN_DATA"] = str(tmp_path / "data")
    assert brain_setting(tmp_path / "data", environ, carry_over=False) == (None, "not configured")
    assert brain_setting(tmp_path / "data", environ)[0] == tmp_path


def test_claudes_settings_that_cannot_be_read_carry_nothing_over(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text("{broken", "utf-8")
    environ = {"CLAUDE_PLUGIN_ROOT": str(PLUGIN), "CLAUDE_CONFIG_DIR": str(tmp_path / ".claude")}
    assert brain_setting(tmp_path / "data", environ) == (None, "not configured")


@pytest.mark.skipif(sys.platform != "win32", reason="Git Bash drives are a Windows form")
def test_a_git_bash_drive_is_read_as_its_windows_drive():
    assert host_path("/d/Projects/Brain") == host_path("D:/Projects/Brain")
    assert host_path("/c") == host_path("C:")
    assert host_path("/data/Brain").drive == ""


def test_the_data_folder_is_the_first_variable_set_skipping_unexpanded_ones(tmp_path):
    environ = {
        "BRAIN_DATA_DIR": "${CLAUDE_PLUGIN_DATA}",
        "CLAUDE_PLUGIN_DATA": "",
        "PLUGIN_DATA": str(tmp_path / "plugin data"),
        "COPILOT_PLUGIN_DATA": str(tmp_path / "copilot"),
    }
    assert data_dir(None, environ) == ((tmp_path / "plugin data").resolve(), "from PLUGIN_DATA")
    environ["BRAIN_DATA_DIR"] = str(tmp_path / "override")
    assert data_dir(None, environ) == ((tmp_path / "override").resolve(), "from BRAIN_DATA_DIR")


def test_with_no_host_folder_the_data_folder_is_the_users_own(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    path, why = data_dir(None, {"LOCALAPPDATA": str(tmp_path / "Local"), "XDG_DATA_HOME": str(tmp_path / "share")})
    assert path.name in ("AI.Brain", "ai-brain") and path.is_relative_to(tmp_path)
    assert why.startswith("no host named one")


def test_a_data_folder_inside_the_brain_or_the_plugin_is_refused(tmp_path):
    with pytest.raises(FolderError, match="inside the Brain folder"):
        data_dir(tmp_path, {"BRAIN_DATA_DIR": str(tmp_path / "state")})
    with pytest.raises(FolderError, match="inside the plugin's install folder"):
        data_dir(None, {"BRAIN_DATA_DIR": str(PLUGIN / "data")})
