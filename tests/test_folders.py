import pytest

from server.folders import PLUGIN, FolderError, brain_dir, data_dir


def test_the_brain_folder_comes_from_brain_dir(tmp_path):
    assert brain_dir({"BRAIN_DIR": str(tmp_path)}) == tmp_path.resolve()


@pytest.mark.parametrize("value", [None, "", "  ", "${user_config.brain_folder}"])
def test_an_unset_or_unexpanded_brain_folder_is_refused(value):
    environ = {} if value is None else {"BRAIN_DIR": value}
    with pytest.raises(FolderError, match="BRAIN_DIR is not set"):
        brain_dir(environ)


def test_a_brain_folder_that_does_not_exist_is_refused_not_created(tmp_path):
    missing = tmp_path / "unmounted drive" / "Brain"
    with pytest.raises(FolderError, match="does not exist"):
        brain_dir({"BRAIN_DIR": str(missing)})
    assert not missing.exists()


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
