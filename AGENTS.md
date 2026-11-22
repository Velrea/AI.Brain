# AGENTS.md

- This repository is public. Nothing committed, including commit messages and pull request text, names a private repository, an internal system, a machine path, or a person's private details.
- Tests live under `tests/`, never under `plugin/`.
- The plugin's entry in `.claude-plugin/marketplace.json` carries only the name and the source.
- Run the plugin under development with `claude --plugin-dir plugin`, not from a marketplace install.
- Only `plugin/server/serve.py` may import a third-party package. The core module, the launcher, and `folders.py` run outside the pinned environment and use the standard library only.
- Nothing in the plugin deletes the local index file, and its name carries no version. A change to the index's schema only adds tables, indexes, triggers, or columns, never alters or drops one, and must work on an index any earlier version built.
- Any change under `plugin/` raises the `version` in `plugin/plugin.json`.
- Never edit `plugin/requirements.txt` by hand. Change `plugin/requirements.in` and recompile it as `docs/development.md` says.
- The launcher and the server write nothing to stdout, which is the server's channel to its host; diagnostics go to stderr.
- Whatever is on `main` is shipped to installs nobody can see. A change to settings, manifests, the data folder, or a format carries an existing install across.
- The plugin runs on Windows, macOS, and Linux. Never ship a path, command, or script that works on only one.
- Examples in docs, tests, and commit text are obviously fictional, never realistic health, people, or life details.
- Plugin text says what was recorded or what happened. It never says "the user's life" and names no use case.
