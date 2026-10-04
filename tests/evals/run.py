"""Runs the eval suite: the cases in `cases.py`, played through a model by
Claude Code's plugin evals, each run against its own copy of the seeded Brain.

    python tests/evals/run.py [--bash] [claude plugin eval options]

Plugin evals read a suite only from inside the plugin under test, and the
suite lives under `tests/`, so this assembles a copy of the plugin with the
cases written into its `evals/`, in `tests/evals/.cache/harness/`. Each run
loads only that plugin and starts its real MCP server, through the plugin's
own config, hook, and launcher. Results go to `tests/evals/results/`.

The cases tagged `bash` file documents through the document skill's script,
so they need a shell, which an eval run grants only where Claude Code can
sandbox it: macOS, Linux, and WSL2. They run there, and are left out, saying
so, where it cannot, as on Windows. `--bash` includes them anyway.

Any other option goes to `claude plugin eval` as it is, such as `--case`,
`--tag`, `--runs`, `--model`, or `-j`.
"""

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import cases  # noqa: E402

PLUGIN = HERE.parent.parent / "plugin"
CACHE = HERE / ".cache"
HARNESS = CACHE / "harness"
DATA = CACHE / "data"
"""Where the launcher builds the server's environment once, for every run to copy."""
RESULTS = HERE / "results"
TOOLS = "mcp__plugin_brain_brain__*"
ALLOWED = ["Skill", "Read", "Glob", "Grep"]
JUDGE = "sonnet"
"""The model for judged graders, unless `--judge-model` is given."""


def main(argv: list[str]) -> int:
    bash = "--bash" in argv or sys.platform != "win32"
    passed = [arg for arg in argv if arg != "--bash"]
    chosen = [case for case in cases.CASES if bash or "bash" not in case.tags]
    if len(chosen) < len(cases.CASES):
        left_out = ", ".join(case.name for case in cases.CASES if case not in chosen)
        print(f"Left out, needing a shell an eval run cannot sandbox on Windows: {left_out}."
              " Run them on macOS, Linux, or WSL2.", file=sys.stderr)
    venv = prepare()
    assemble(chosen, venv)
    claude = shutil.which("claude")
    if claude is None:
        print("Claude Code's claude command is not on the PATH.", file=sys.stderr)
        return 1
    output = RESULTS / dt.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    # The default judge, the small background model, failed correct answers over
    # how a name or a date was written.
    judge = [] if "--judge-model" in passed else ["--judge-model", JUDGE]
    command = [
        claude, "plugin", "eval", str(HARNESS),
        "--scaffold", "--mocks", "off", "--trust-plugin", "--no-publish", "--ablation", "none",
        "--output-dir", str(output), *judge, *passed,
        "--allow-tools", TOOLS, *(["Bash"] if bash else []),
    ]
    return subprocess.run(command).returncode


def prepare() -> Path:
    """The server's environment, built by the plugin's own launcher, which
    rebuilds it only when the pins change."""
    script = PLUGIN / "scripts" / ("brain.cmd" if os.name == "nt" else "brain")
    subprocess.run([str(script), "prepare"], env=os.environ | {"BRAIN_DATA_DIR": str(DATA)}, check=True)
    return DATA / "venv"


def assemble(chosen: list[cases.Case], venv: Path) -> None:
    """A copy of the plugin with each case written into its `evals/`."""
    shutil.rmtree(HARNESS, ignore_errors=True)
    shutil.copytree(PLUGIN, HARNESS, ignore=shutil.ignore_patterns("__pycache__"))
    setup = HERE / "setup_run.py"
    for case in chosen:
        folder = HARNESS / "evals" / case.name
        (folder / "graders").mkdir(parents=True)
        (folder / "case.yaml").write_text(
            f'schema_version: "1.1"\nname: {case.name}\ncontext:\n  scaffold_script: setup.sh\n', "utf-8")
        (folder / "setup.sh").write_text(
            f'#!/bin/bash\nexec "{_posix(sys.executable)}" "{_posix(setup)}" {case.name} "{_posix(venv)}"\n',
            "utf-8", newline="\n")
        run = {"tags": case.tags, "max_turns": case.max_turns, "timeout_seconds": case.timeout_seconds,
               "allowed_tools": ALLOWED}
        (folder / "prompt.md").write_text(_frontmatter(run) + "\n" + case.prompt + "\n", "utf-8")
        for name, grader in case.graders.items():
            grader = dict(grader)
            body = textwrap.dedent(grader.pop("body", "")).strip()
            (folder / "graders" / f"{name}.md").write_text(
                _frontmatter(grader) + ("\n" + body + "\n" if body else ""), "utf-8")


def _frontmatter(fields: dict) -> str:
    # JSON is YAML, and a double-quoted JSON string keeps every backslash of a regex.
    return "---\n" + "".join(f"{key}: {json.dumps(value)}\n" for key, value in fields.items()) + "---\n"


def _posix(path: str | Path) -> str:
    return Path(path).as_posix()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
