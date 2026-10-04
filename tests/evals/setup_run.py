"""Sets up one eval run, before Claude starts, as each case's scaffold.

It runs in the run's empty workspace, with `HOME` set to the run's own home,
and gives the run what a configured machine has:

- its own copy of the seeded Brain, in `brain/`;
- the files the case hands over, in `inbox/`;
- the Brain folder setting, which an eval run otherwise leaves empty, so the
  server would not start and the skills would name no folder;
- the server's Python environment, built once by the launcher and copied
  into the run's plugin data folder, which the launcher then finds ready
  instead of spending minutes installing it in every run.

    setup_run.py <case> <venv>
"""

import json
import os
import shutil
import sys
from pathlib import Path

import cases
import seed

PLUGIN_ID = "brain@inline"
"""How the eval run names a plugin it loads from a folder."""


def main(case_name: str, venv: Path) -> int:
    [case] = [case for case in cases.CASES if case.name == case_name]
    work = Path.cwd()
    shutil.copytree(seed.BRAIN, work / "brain")
    for name, data in case.inbox.items():
        (work / "inbox").mkdir(exist_ok=True)
        (work / "inbox" / name).write_bytes(data)
    # The run's Claude Code configuration sits beside its home.
    config = Path(os.environ["HOME"]).parent / "config"
    if not config.is_dir():
        print(f"no Claude Code configuration beside the run's home at {config}: the eval run's layout has"
              " changed, so the Brain folder setting cannot be given", file=sys.stderr)
        return 1
    settings_path = config / "settings.json"
    settings = json.loads(settings_path.read_text("utf-8")) if settings_path.exists() else {}
    settings.setdefault("pluginConfigs", {})[PLUGIN_ID] = {"options": {"brain_folder": str(work / "brain")}}
    settings_path.write_text(json.dumps(settings, indent=2), "utf-8")
    data = config / "plugins" / "data" / PLUGIN_ID.replace("@", "-")
    data.mkdir(parents=True, exist_ok=True)
    shutil.copytree(venv, data / "venv", symlinks=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], Path(sys.argv[2])))
