# Development

How to run the tests, run the plugin under development, and keep its pinned packages current. How the plugin is built is in [the core module](core-module.md), [the MCP server](mcp-server.md), and [the skills](skills.md).

## Tests

The tests need Python 3.11 or later, the packages the plugin pins in [`plugin/requirements.txt`](../plugin/requirements.txt), and pytest. The core module needs no package: it reads through the SQLite built into Python, which must include full-text search, as the builds from python.org and most Linux distributions do. From the repository root:

```bash
python -m venv .venv
```

```bash
.venv/Scripts/python -m pip install -r plugin/requirements.txt
```

```bash
.venv/Scripts/python -m pip install pytest
```

```bash
.venv/Scripts/python -m pytest
```

On macOS or Linux the venv's Python is `.venv/bin/python`. Every pull request, and every push to `main`, runs the same tests on Windows, Linux, and macOS, on Python 3.11 and 3.14, and a pull request cannot merge until they pass.

The [evals](evals.md) test the whole plugin played through a model, against a fictional Brain. They cost model calls, so they run on demand rather than on every pull request.

## Running the plugin

Run the plugin under development with `claude --plugin-dir plugin`, rather than from a marketplace install, so Claude Code loads the working copy.

## Pinned packages

`plugin/requirements.txt` pins every package the server needs to an exact version, for every platform. It is compiled from [`plugin/requirements.in`](../plugin/requirements.in), which names only the packages the server uses directly. Dependabot opens a pull request each week bumping the pins, and one for a security fix as soon as it is published; the tests run on it before it merges. To regenerate the pins by hand, use [uv](https://docs.astral.sh/uv/) from `plugin/`:

```bash
uv pip compile --universal --python-version 3.11 --no-annotate --output-file requirements.txt requirements.in
```
