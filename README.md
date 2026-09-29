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

- [Design](docs/design/): what the Brain is and does.
- [Architecture](docs/architecture/): how it is built, including the data format.
- [Work](docs/work/): what is committed to next.
- [Ideas](docs/ideas/): what might be worth doing, with no commitment.

## License

[Elastic License 2.0](LICENSE): you may use, copy, modify, and share it, but not offer it to others as a hosted or managed service.
