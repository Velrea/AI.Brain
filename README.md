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

## Documents

- [The Brain](docs/brain.md): what the Brain is and does.
- [Reading and writing](docs/read-and-write.md): how the record is read and written.
- [Data format](docs/data-format.md): the on-disk layout and the record.
- [The plugin](docs/plugin.md): the MCP server, its configuration, tools, and skills.
- [Work](docs/work/): what is committed to next.
- [Ideas](docs/ideas/): what might be worth doing, with no commitment.

## License

[Elastic License 2.0](LICENSE): you may use, copy, modify, and share it, but not offer it to others as a hosted or managed service.
