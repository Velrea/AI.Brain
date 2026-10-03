"""Prepares this machine for the Brain's MCP server, then starts it.

Run by the machine's own Python 3, through `scripts/brain`, so standard
library only. `prepare` builds a virtual environment in the plugin data
folder and installs the pinned packages of `requirements.txt` into it, again
only when they change; the plugin's SessionStart hook runs it as a session
opens. With no argument, it prepares the same way, then starts the server in
that environment. Nothing goes to stdout, which is the server's channel to
its host and, for the hook, context for the model.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

MINIMUM = (3, 11)

if sys.version_info < MINIMUM:
    sys.exit(f"The Brain needs Python {'.'.join(map(str, MINIMUM))} or later; this is {sys.version.split()[0]}.")

PLUGIN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN))

from brain.lock import FileLock  # noqa: E402
from server.folders import FolderError, data_dir  # noqa: E402

REQUIREMENTS = PLUGIN / "requirements.txt"
PREPARE_TIMEOUT = 600.0
"""Seconds a session waits while another builds the environment."""


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def prepare(data: Path, requirements: Path = REQUIREMENTS) -> Path:
    """The Python of a virtual environment in `data` that holds exactly the
    pinned packages of `requirements`, built first if it does not. Sessions
    take turns, so one that finds another building waits for it."""
    venv = data / "venv"
    python = venv_python(venv)
    wanted = requirements.read_bytes()
    installed = venv / "requirements.txt"
    with FileLock(data / "venv.lock", PREPARE_TIMEOUT):
        if installed.is_file() and installed.read_bytes() == wanted and _runs(python):
            return python
        print(f"Brain: preparing {venv}", file=sys.stderr)
        # Rebuilt whole, so no package an older pin installed lingers.
        shutil.rmtree(venv, ignore_errors=True)
        _run([sys.executable, "-m", "venv", str(venv)])
        _run([
            str(python), "-m", "pip", "install", "--no-input",
            "--disable-pip-version-check", "--quiet", "-r", str(requirements),
        ])
        # Written last: an environment without it is one a crash left half built.
        installed.write_bytes(wanted)
    return python


def _runs(python: Path) -> bool:
    """Whether the environment's Python still starts: one whose base Python was
    removed or upgraded away does not."""
    try:
        return subprocess.run([str(python), "-c", ""], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    except OSError:
        return False


def _run(command: list[str]) -> None:
    result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Brain: {' '.join(command[:4])} … failed with exit code {result.returncode}")


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "serve"
    if command not in ("prepare", "serve"):
        print(f"Brain: unknown command {command!r}; use prepare, or none to serve", file=sys.stderr)
        return 2
    try:
        data, why = data_dir(None)
        python = prepare(data)
    except (FolderError, RuntimeError, OSError) as error:
        print(f"Brain: {error}", file=sys.stderr)
        return 1
    if command == "prepare":
        return 0
    print(f"Brain: plugin data folder {data} ({why})", file=sys.stderr)
    env = os.environ | {"PYTHONPATH": str(PLUGIN), "BRAIN_DATA_DIR": str(data)}
    args = [str(python), "-m", "server.serve"]
    if os.name != "nt":
        os.execve(python, args, env)
    # Windows has no exec: the server runs as a child on the same stdin and stdout.
    return subprocess.run(args, env=env).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv))
