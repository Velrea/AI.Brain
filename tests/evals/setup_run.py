"""Sets up one eval run, before Claude starts, as each case's scaffold.

It runs in the run's empty workspace, with `HOME` set to the run's own home,
and gives the run what a configured machine has:

- its own copy of the seeded Brain, in `brain/`;
- the files the case hands over, in `inbox/`, and any other file it writes,
  replaces, or removes, the seeded Brain's documents among them;
- the install's settings, in the run's plugin data folder, naming that copy
  as the Brain folder, which a new install would otherwise ask for;
- the server's Python environment, built once by the launcher and copied
  into the same folder, which the launcher then finds ready instead of
  spending minutes installing it in every run.

    setup_run.py <case> <venv>
"""

import json
import os
import shutil
import sys
from pathlib import Path

import cases
import seed
from server.folders import SETTINGS

PLUGIN_ID = "brain@inline"
"""How the eval run names a plugin it loads from a folder."""


def main(case_name: str, venv: Path) -> int:
    [case] = [case for case in cases.CASES if case.name == case_name]
    work = Path.cwd()
    shutil.copytree(seed.BRAIN, work / "brain")
    for name, data in case.inbox.items():
        (work / "inbox").mkdir(exist_ok=True)
        (work / "inbox" / name).write_bytes(data.replace(b"{workspace}", work.as_uri().encode()))
    for path, data in case.files.items():
        file = work / path
        if data is None:
            file.unlink()
        else:
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
    # The run's Claude Code configuration sits beside its home, with the plugin's data folder in it.
    config = Path(os.environ["HOME"]).parent / "config"
    if not config.is_dir():
        print(f"no Claude Code configuration beside the run's home at {config}: the eval run's layout has"
              " changed, so the install's settings cannot be given", file=sys.stderr)
        return 1
    data = config / "plugins" / "data" / PLUGIN_ID.replace("@", "-")
    data.mkdir(parents=True, exist_ok=True)
    (data / SETTINGS).write_text(json.dumps({"brain_folder": str(work / "brain")}, indent=2), "utf-8")
    shutil.copytree(venv, data / "venv", symlinks=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], Path(sys.argv[2])))
