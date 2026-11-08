"""Prepares this machine for the Brain's MCP server, then starts it.

Run by the machine's own Python 3, through `scripts/brain`, so standard
library only. `prepare` builds a virtual environment in the plugin data
folder and installs the pinned packages of `requirements.txt` into it, again
only when they change. With no argument, it prepares the same way, then
starts the server in that environment. Nothing goes to stdout, which is the
server's channel to its host.

The build runs in a process of its own, detached, logging to `venv.log` in
the data folder: a host that stops waiting for a server kills the launcher,
and with it any build the launcher ran, so a first start that outlasted the
host would otherwise never finish, and every start would begin it again.
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
from server.folders import FolderError, brain_setting, data_dir  # noqa: E402

REQUIREMENTS = PLUGIN / "requirements.txt"
PREPARE_TIMEOUT = 600.0
"""Seconds a session waits while another builds the environment."""
BUILD_LOG = "venv.log"
"""The build's output, in the data folder."""


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def prepare(data: Path, requirements: Path = REQUIREMENTS) -> Path:
    """The Python of a virtual environment in `data` that holds exactly the
    pinned packages of `requirements`, built first, in a detached process,
    if it does not."""
    python = venv_python(data / "venv")
    if _ready(data, requirements):
        return python
    data.mkdir(parents=True, exist_ok=True)
    log = data / BUILD_LOG
    with open(log, "wb") as output:
        builder = _detached([sys.executable, str(Path(__file__).resolve()), "build", str(data), str(requirements)], output)
    print(f"Brain: preparing {data / 'venv'}, logging to {log}", file=sys.stderr)
    builder.wait()
    if not _ready(data, requirements):
        raise RuntimeError(f"Brain: preparing {data / 'venv'} failed: {log.read_text('utf-8', 'replace')[-2000:]}")
    return python


def _ready(data: Path, requirements: Path) -> bool:
    """Whether the environment in `data` holds exactly the pins of `requirements`, and its Python runs."""
    installed = data / "venv" / "requirements.txt"
    return installed.is_file() and installed.read_bytes() == requirements.read_bytes() and _runs(venv_python(data / "venv"))


def _detached(command: list[str], output) -> subprocess.Popen:
    """Starts `command` in a process of its own, which goes on when this one is killed."""
    if os.name != "nt":
        return subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output, stderr=output, start_new_session=True)
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        # Out of the host's job too, where the job allows it, so closing the job does not end it.
        return subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB)
    except OSError:
        return subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output, stderr=output, creationflags=flags)


def build(data: Path, requirements: Path) -> None:
    """Builds the environment `prepare` asks for, unless it is ready. Sessions
    take turns, so one that finds another building waits for it."""
    venv = data / "venv"
    python = venv_python(venv)
    wanted = requirements.read_bytes()
    installed = venv / "requirements.txt"
    with FileLock(data / "venv.lock", PREPARE_TIMEOUT):
        if _ready(data, requirements):
            return
        # Rebuilt whole, so no package an older pin installed lingers.
        shutil.rmtree(venv, ignore_errors=True)
        _run([sys.executable, "-m", "venv", str(venv)])
        _run([
            str(python), "-m", "pip", "install", "--no-input",
            "--disable-pip-version-check", "--quiet", "-r", str(requirements),
        ])
        # Written last: an environment without it is one a crash left half built.
        installed.write_bytes(wanted)


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
    if command == "build" and len(argv) == 4:
        # The detached build `prepare` starts.
        try:
            build(Path(argv[2]), Path(argv[3]))
        except (RuntimeError, OSError, TimeoutError) as error:
            print(f"Brain: {error}", file=sys.stderr)
            return 1
        return 0
    if command not in ("prepare", "serve"):
        print(f"Brain: unknown command {command!r}; use prepare, or none to serve", file=sys.stderr)
        return 2
    try:
        data, why = data_dir(None)
        # Checked before preparing, so an environment is never built inside the Brain
        # folder. Any other trouble with the Brain folder is the server's to report.
        try:
            brain, _ = brain_setting(data, carry_over=False)
        except FolderError:
            brain = None
        if brain is not None:
            data_dir(brain)
        python = prepare(data)
    except (FolderError, RuntimeError, OSError) as error:
        print(f"Brain: {error}", file=sys.stderr)
        return 1
    if command == "prepare":
        return 0
    print(f"Brain: plugin data folder {data} ({why})", file=sys.stderr)
    env = os.environ | {"PYTHONPATH": str(PLUGIN), "PLUGIN_DATA": str(data)}
    args = [str(python), "-m", "server.serve"]
    if os.name != "nt":
        os.execve(python, args, env)
    # Windows has no exec: the server runs as a child on the same stdin and stdout.
    return subprocess.run(args, env=env).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv))
