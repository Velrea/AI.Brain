import subprocess
import sys

from conftest import PLUGIN
from server.launch import main, prepare, venv_python


def test_prepare_builds_an_environment_once_and_again_when_the_pins_change(tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("")
    data = tmp_path / "data"

    python = prepare(data, requirements)
    assert python == venv_python(data / "venv")
    assert subprocess.run([str(python), "-c", "import sys; assert sys.prefix != sys.base_prefix"]).returncode == 0
    built = python.stat().st_mtime_ns

    assert prepare(data, requirements) == python
    assert python.stat().st_mtime_ns == built

    requirements.write_text("# changed\n")
    marker = data / "venv" / "marker"
    marker.write_text("left by the old environment")
    prepare(data, requirements)
    assert not marker.exists()
    assert (data / "venv" / "requirements.txt").read_text() == "# changed\n"


def test_a_half_built_environment_is_rebuilt(tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("")
    data = tmp_path / "data"
    prepare(data, requirements)
    (data / "venv" / "requirements.txt").unlink()
    marker = data / "venv" / "marker"
    marker.write_text("")

    prepare(data, requirements)
    assert not marker.exists()


def test_an_unknown_command_is_refused(capsys):
    assert main(["launch.py", "start"]) == 2
    assert "unknown command" in capsys.readouterr().err


def test_an_old_python_is_refused_before_anything_runs():
    launch = PLUGIN / "server" / "launch.py"
    code = f"import runpy, sys; sys.version_info = (3, 10, 0); runpy.run_path({str(launch)!r}, run_name='__main__')"

    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)

    assert done.returncode == 1
    assert done.stdout == ""
    assert "needs Python 3.11 or later" in done.stderr


def test_the_launch_script_finds_python_and_passes_its_arguments_and_exit_code():
    if sys.platform == "win32":
        command = ["cmd", "/c", str(PLUGIN / "scripts" / "brain.cmd"), "bogus"]
    else:
        command = ["sh", str(PLUGIN / "scripts" / "brain"), "bogus"]

    done = subprocess.run(command, capture_output=True, text=True)

    assert done.returncode == 2
    assert done.stdout == ""
    assert "unknown command 'bogus'" in done.stderr
