# Heroquarium ArtGen plugin

Isometric pixel-art generation for Heroquarium, exposed as MCP tools, with a
bundled usage skill.

## Contents

- `.claude-plugin/plugin.json` — manifest (name, version).
- `.mcp.json` — starts the `heroquarium-artgen` stdio MCP server.
- `mcp/server.py` — the server (tools: terrain, water, coast, house, prop, tree,
  actor, actor_walk, anim, list_palette, list_roster).
- `skills/heroquarium-artgen/SKILL.md` — how a session should use the tools.
- `artgen/`, `palette.json` — the generation library the server imports.

## Requirements (this is the usual reason tools don't appear)

The MCP server is a stdio process launched via `.mcp.json` as `python3
mcp/server.py`. If the `mcp`, `pillow`, or `numpy` packages are **not installed
in the exact Python that `python3` resolves to**, the process exits on launch
and Cowork shows the server as "connecting" with **no tools** — silently.

Fix — install the deps into that interpreter:

```bash
pip install -r requirements.txt      # pillow, numpy, mcp
```

### Verify it can start

Run the server by hand from the plugin folder:

```bash
python3 mcp/server.py
```

- **Correct:** it prints nothing and just blocks (it's waiting on stdio). Ctrl-C to stop.
- **Broken:** it prints an error and exits — read it, then check `mcp/startup.log`
  (written on every launch). The `executable=` line shows which Python ran; the
  `dep ...: MISSING` lines show what to install for that Python.

If `python3` in Cowork's environment is a different interpreter than your shell,
either install the deps for that one, or edit `.mcp.json` to use an absolute
python path (e.g. `"command": "/usr/bin/python3"`).

## Install

Save the `.plugin` file from the build folder and install it via the Cowork
app, or register the server directly:

```bash
claude mcp add heroquarium-artgen -- python3 /abs/path/to/plugin/mcp/server.py
```

Built artifacts live in the repo's `build/` folder, one versioned `.plugin`
per build (see `build/BUILDS.md`).
