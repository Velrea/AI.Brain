---
status: ready
claimed-by:
branch:
---

# Types

The `journal-entry` and `snapshot` definitions, and validation against them.

## Acceptance criteria

- `journal-entry` and `snapshot` ship with the plugin as definitions, in the shape a user-defined type uses.
- Creating a Brain records both definitions into it.
- A record is accepted only when it satisfies its definition and every definition above it.
- A definition that redefines an envelope key or an inherited property is rejected.
