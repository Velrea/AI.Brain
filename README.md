# AI.Brain

A personal knowledge base run by Claude. You tell Claude what happened, Claude asks follow-up questions and records it, and later Claude answers questions about your life by reading the record back. It ships as a plugin with an MCP server inside it, and keeps its records on the local file system, where a sync service such as Google Drive or Dropbox can back them up.

The plugin is in development: its MCP server works, and the skills that use it are not written yet.

## Add the marketplace

```bash
claude plugin marketplace add Velrea/AI.Brain
```

```bash
claude plugin install brain@ai-brain
```

When the plugin is enabled, Claude Code asks for your Brain folder. Choose a folder inside a synced folder, such as Google Drive or Dropbox, and choose the same one on every machine. The plugin keeps its records in `events/` and its filed documents in `documents/` inside it.

The plugin needs Python 3.11 or later on the machine: `python3` or `python` on macOS and Linux, `python` or `py` on Windows. The first session after installing or updating it downloads the packages the plugin pins, which takes about 20 seconds and needs a connection.

## What it does

- **Capture.** You tell Claude what happened, in as much detail as you have. Claude asks follow-up questions to fill in what is missing, then records it, and records a life event unprompted when one surfaces in conversation.
- **Accurate retrieval.** What happened, how things stand now, what changed, fast enough to feel conversational.
- **Corrections.** A mistake or a later update can be recorded, and every later answer reflects it.
- **Documents.** Original files are kept, linked to what they are about, and retrievable.

## Documents

- [The core module](docs/core-module.md): the Python package that holds the file format, writes the records, and reads them back.
- [The MCP server](docs/mcp-server.md): how an agent reaches the Brain, and how the plugin prepares the machine to run it.
- [Work](docs/work/): what is being built, and the choices already settled for it.
- [Ideas](docs/ideas/): what might be worth doing, with no commitment.

## Development

The tests need Python 3.11 or later, the packages the plugin pins in [`plugin/requirements.txt`](plugin/requirements.txt), and pytest. The core module needs no package: it reads through the SQLite built into Python, which must include full-text search, as the builds from python.org and most Linux distributions do. From the repository root:

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

Run the plugin under development with `claude --plugin-dir plugin`.

`plugin/requirements.txt` pins every package the server needs to an exact version, for every platform. Dependabot opens a pull request each week bumping the pins, and one for a security fix as soon as it is published; the tests run on it before it merges. To regenerate the pins by hand, use [uv](https://docs.astral.sh/uv/):

```bash
echo "mcp==2.3.0" | uv pip compile - --universal --python-version 3.11 --no-header --no-annotate -o plugin/requirements.txt
```

On macOS or Linux the venv's Python is `.venv/bin/python`. Every pull request runs the same tests on Windows, Linux, and macOS, and cannot merge until they pass.

## License

[Elastic License 2.0](LICENSE): you may use, copy, modify, and share it, but not offer it to others as a hosted or managed service.
