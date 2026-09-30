# Types

Every record is validated against its type, so the structure of the record is enforced by code rather than by the model.

## Settled

Every type extends `journal-entry`, which is the envelope and the fields the log carries:

```
journal-entry        the envelope and the log's fields
├─ snapshot          + scope, read_upto
└─ definition        + name, version, extends, properties, required; body = instructions for the model
```

- **A type is defined by a `definition` record** in the Brain itself, so a Brain carries the definitions its records were written under. `definition` is the one type the code interprets natively.
- **A definition extends exactly one other and inherits its properties**, and may not redefine an envelope key or an inherited property.
- **A type's format evolves by version.** `v` rises when a definition changes, and a reader translates older versions as it reads them. A written record is never rewritten.

## Done when

- `journal-entry` and `snapshot` ship with the plugin as definitions, in the shape a user-defined type uses.
- Creating a Brain records both definitions into it.
- A record is accepted only when it satisfies its definition and every definition above it.
- A definition that redefines an envelope key or an inherited property is rejected.
