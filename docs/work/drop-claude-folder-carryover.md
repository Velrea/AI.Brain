# Drop the Claude folder carry-over

Removes the step that copies an existing Claude install's Brain folder from Claude Code's settings, in the release after the one that adds it, by when existing installs have updated.

## Depends on

- [Every host](every-host.md), released.

## Done when

- The server no longer reads Claude Code's settings, and its tests and docs no longer mention them.
