"""The two folders the server works in: the plugin data folder it finds on this
machine, and the synced Brain folder this install is set to, kept in the data
folder's settings.

Standard library only, so the launcher can use it before the server's
packages are installed.
"""

import json
import os
import re
import sys
import uuid
from collections.abc import Mapping
from pathlib import Path

from brain.format import brain_key

PLUGIN = Path(__file__).resolve().parent.parent
"""The plugin's install folder, replaced on every update."""

DATA_VARIABLE = "BRAIN_DATA_DIR"
"""The install's data folder, when its host's manifest names one."""

SETTINGS = "settings.json"
"""The install's settings, in its plugin data folder."""


class FolderError(RuntimeError):
    """A folder the server cannot work in."""


class NotConfigured(FolderError):
    """No Brain folder is set for this install."""


class BrainMissing(FolderError):
    """The Brain folder set for this install does not exist."""

    def __init__(self, path: Path):
        super().__init__(f"the Brain folder {str(path)!r} does not exist: is its sync folder available?")
        self.path = path


def data_dir(brain: Path | None, environ: Mapping[str, str] = os.environ) -> tuple[Path, str]:
    """The plugin data folder and why it was chosen: `DATA_VARIABLE` when set,
    and otherwise a fixed folder for the user. It is never inside `brain`,
    when given, or the plugin's install folder."""
    value = _set(environ.get(DATA_VARIABLE))
    if value is not None:
        path, why = Path(value).expanduser().resolve(), f"from {DATA_VARIABLE}"
    else:
        path, why = _user_folder(environ), f"{DATA_VARIABLE} is not set"
    for outside, name in ((brain, "the Brain folder"), (PLUGIN, "the plugin's install folder")):
        if outside is not None and path.is_relative_to(outside.resolve()):
            raise FolderError(f"the plugin data folder {str(path)!r} ({why}) is inside {name}")
    return path, why


def brain_setting(data: Path, environ: Mapping[str, str] = os.environ, *, carry_over: bool = True) -> tuple[Path | None, str]:
    """The Brain folder this install is set to and where it was set, or None:
    `BRAIN_DIR` when set, then the data folder's settings. With no settings
    and `carry_over`, an install from before the folder was kept here keeps
    it: the folder Claude Code's own settings keep for this plugin, when this
    install has already used it, is written to the data folder's settings and
    returned. Whether the folder exists is not checked."""
    value = _set(environ.get("BRAIN_DIR"))
    if value is not None:
        return host_path(value), "from BRAIN_DIR"
    settings = Path(data) / SETTINGS
    if settings.is_file():
        try:
            folder = json.loads(settings.read_text("utf-8")).get("brain_folder")
        except (OSError, ValueError, AttributeError) as error:
            raise FolderError(f"the settings at {str(settings)!r} cannot be read ({error}): configure the Brain folder again") from error
        if not isinstance(folder, str) or not Path(folder).is_absolute():
            raise FolderError(f"the settings at {str(settings)!r} name no Brain folder: configure the Brain folder again")
        return Path(folder), f"from {SETTINGS}"
    claude = _from_claude(Path(data), environ) if carry_over else None  # Dropped in the next release.
    if claude is not None:
        _write_settings(Path(data), claude)
        return claude, "carried over from Claude Code's settings"
    return None, "not configured"


def existing(path: Path) -> Path:
    """`path` resolved, when it is a folder. A Brain folder must exist: a sync
    folder that is not mounted must not quietly become a new, empty Brain."""
    if not path.is_dir():
        if path.exists():
            raise FolderError(f"the Brain folder {str(path)!r} is not a folder")
        raise BrainMissing(path)
    return path.resolve()


def configure(data: Path, folder: str, *, create: bool = False, environ: Mapping[str, str] = os.environ) -> Path:
    """Sets this install's Brain folder to `folder`, an absolute path, creating it
    first only when `create`, and returns it resolved."""
    if _set(environ.get("BRAIN_DIR")) is not None:
        raise FolderError(f"BRAIN_DIR is set to {environ['BRAIN_DIR']!r}, which overrides the configured Brain folder")
    path = host_path(folder)
    if not path.is_absolute():
        raise FolderError(f"{folder!r} is not an absolute path: give the Brain folder's full path")
    if create and not path.exists():
        path.mkdir(parents=True)
    path = existing(path)
    data_dir(path, {"BRAIN_DATA_DIR": str(data)})
    _write_settings(Path(data), path)
    return path


def host_path(value: str) -> Path:
    """`value` as a path on this machine: `~` expanded, and on Windows a drive
    written the way Git Bash writes it read as that drive."""
    if sys.platform == "win32":
        value = re.sub(r"^/([A-Za-z])(?=/|$)", lambda drive: f"{drive[1].upper()}:", value)
    return Path(value).expanduser()


def _from_claude(data: Path, environ: Mapping[str, str]) -> Path | None:
    """The one Brain folder Claude Code's own settings keep for this plugin,
    from when it was a setting Claude Code asked for, that the install with
    data folder `data` has already used: None when there is none, several,
    or settings that cannot be read. A fresh install has used none, so it
    never takes another install's folder. Only read, never written."""
    root = _set(environ.get("CLAUDE_CONFIG_DIR"))
    try:
        settings = (Path(root).expanduser() if root else Path.home() / ".claude") / "settings.json"
        configs = json.loads(settings.read_text("utf-8")).get("pluginConfigs")
    except (OSError, ValueError, AttributeError, RuntimeError):
        return None
    if not isinstance(configs, dict):
        return None
    found = set()
    for key, config in configs.items():
        options = config.get("options") if isinstance(config, dict) else None
        if key.split("@")[0] == "brain" and isinstance(options, dict):
            folder = _set(options.get("brain_folder")) if isinstance(options.get("brain_folder"), str) else None
            if folder is not None and Path(folder).is_absolute():
                found.add(str(Path(folder)))
    # The core module names an install's files for a Brain by its key.
    used = [folder for folder in found if any(data.glob(f"{brain_key(Path(folder))}.*"))]
    return Path(used[0]) if len(used) == 1 else None


def _write_settings(data: Path, folder: Path) -> None:
    data.mkdir(parents=True, exist_ok=True)
    temp = data / f".{SETTINGS}.{uuid.uuid4().hex}.tmp"
    temp.write_text(json.dumps({"brain_folder": str(folder)}, indent=2) + "\n", "utf-8")
    os.replace(temp, data / SETTINGS)


def _set(value: str | None) -> str | None:
    """The value, unless it is empty or a `${...}` the host did not expand."""
    if not value or not value.strip() or "${" in value:
        return None
    return value


def _user_folder(environ: Mapping[str, str]) -> Path:
    home = Path.home()
    if sys.platform == "win32":
        return Path(environ.get("LOCALAPPDATA") or home / "AppData" / "Local") / "AI.Brain"
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "AI.Brain"
    return Path(environ.get("XDG_DATA_HOME") or home / ".local" / "share") / "ai-brain"
