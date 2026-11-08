"""Fails a change to `plugin/` that does not raise the plugin's version.

Every merge to `main` is a release, and a host that keeps installed plugins
by version, as Codex does, may take a release only when the version rises.

    python tests/check_version.py <base ref>
"""

import json
import subprocess
import sys

MANIFEST = "plugin/plugin.json"


def version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in json.loads(text)["version"].split("."))


def main(base: str) -> int:
    if subprocess.run(["git", "diff", "--quiet", f"{base}...HEAD", "--", "plugin/"]).returncode == 0:
        return 0
    shown = subprocess.run(["git", "show", f"{base}:{MANIFEST}"], capture_output=True, text=True)
    if shown.returncode != 0:
        # The base has no versioned manifest yet, so any version raises it.
        return 0
    with open(MANIFEST, encoding="utf-8") as manifest:
        now = version(manifest.read())
    before = version(shown.stdout)
    if now <= before:
        print(f"plugin/ changed, so raise the version in {MANIFEST} above {'.'.join(map(str, before))}",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
