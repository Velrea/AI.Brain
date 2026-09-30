# AI.Brain

A personal knowledge base run by Claude. You tell Claude what happened, Claude asks follow-up questions and records it, and later Claude answers questions about your life by reading the record back. It ships as a plugin with an MCP server inside it, and keeps its records on the local file system, where a sync service such as Google Drive or Dropbox can back them up.

The plugin is in development and does not work yet.

## Add the marketplace

```bash
claude plugin marketplace add Velrea/AI.Brain
```

```bash
claude plugin install brain@ai-brain
```

## What it does

- **Capture.** You tell Claude what happened, in as much detail as you have. Claude asks follow-up questions to fill in what is missing, then records it, and records a life event unprompted when one surfaces in conversation.
- **Accurate retrieval.** What happened, how things stand now, what changed, fast enough to feel conversational.
- **Corrections.** A mistake or a later update can be recorded, and every later answer reflects it.
- **Documents.** Original files are kept, linked to what they are about, and retrievable.

## Documents

- [The core module](docs/core-module.md): the Python package that holds the file format and writes the records.
- [Work](docs/work/): what is being built, and the choices already settled for it.
- [Ideas](docs/ideas/): what might be worth doing, with no commitment.

## Development

The tests need Python 3.11 or later and pytest. From the repository root:

```bash
python -m venv .venv
```

```bash
.venv/Scripts/python -m pip install pytest
```

```bash
.venv/Scripts/python -m pytest
```

On macOS or Linux the venv's Python is `.venv/bin/python`. Every pull request runs the same tests on Windows, Linux, and macOS, and cannot merge until they pass.

## License

[Elastic License 2.0](LICENSE): you may use, copy, modify, and share it, but not offer it to others as a hosted or managed service.
