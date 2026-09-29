---
covers: [plugin/**]
---

# The Brain

A personal knowledge base run by Claude: a permanent record of what happens in the user's life, their health, money, home, vehicles, work, and the people around them, plus the source documents behind it. The user tells Claude what happened, Claude asks follow-up questions and records it, and later Claude answers questions about the user's life by reading the record back.

It ships as a Claude Code plugin with an MCP server inside it, and keeps its records on the local file system, where a sync service such as Google Drive or Dropbox can back them up.

## Features

- **Capture.** The user tells Claude what happened, in as much detail as they have. Claude asks follow-up questions to fill in what is missing, then records it. Claude also records a life event unprompted when one surfaces in conversation.
- **Accurate retrieval.** What happened, how things stand now, what changed, fast enough to feel conversational.
- **Corrections.** A mistake or a later update can be recorded, and every later answer reflects it.
- **Documents.** Original files are kept, linked to what they are about, and retrievable.
