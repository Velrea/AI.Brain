"""The two folders the server works in: the synced Brain folder it is given,
and the plugin data folder it finds on this machine.

Standard library only, so the launcher can use it before the server's
packages are installed.
"""

import os
import sys
from collections.abc import Mapping
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
"""The plugin's install folder, replaced on every update."""

DATA_VARIABLES = ("BRAIN_DATA_DIR", "CLAUDE_PLUGIN_DATA", "PLUGIN_DATA", "COPILOT_PLUGIN_DATA")
"""Where hosts name the plugin's data folder, first set first."""


class FolderError(RuntimeError):
    """A folder the server cannot work in."""


def brain_dir(environ: Mapping[str, str] = os.environ) -> Path:
    """The Brain folder, from `BRAIN_DIR`. It must exist: a sync folder that is
    not mounted must not quietly become a new, empty Brain."""
    value = _set(environ.get("BRAIN_DIR"))
    if value is None:
        raise FolderError("BRAIN_DIR is not set: configure the plugin's Brain folder")
    path = Path(value).expanduser()
    if not path.is_dir():
        raise FolderError(f"the Brain folder {str(path)!r} does not exist: is its sync folder available?")
    return path.resolve()


def data_dir(brain: Path | None, environ: Mapping[str, str] = os.environ) -> tuple[Path, str]:
    """The plugin data folder and why it was chosen: the first of
    `DATA_VARIABLES` set, and otherwise a fixed folder for the user. It is
    never inside `brain`, when given, or the plugin's install folder."""
    for name in DATA_VARIABLES:
        value = _set(environ.get(name))
        if value is not None:
            path, why = Path(value).expanduser().resolve(), f"from {name}"
            break
    else:
        path, why = _user_folder(environ), f"no host named one in {', '.join(DATA_VARIABLES)}"
    for outside, name in ((brain, "the Brain folder"), (PLUGIN, "the plugin's install folder")):
        if outside is not None and path.is_relative_to(outside.resolve()):
            raise FolderError(f"the plugin data folder {str(path)!r} ({why}) is inside {name}")
    return path, why


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
