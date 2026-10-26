# Test the connected-agent UX

Run these commands from the repository. Python 3.11+ is required.

```bash
./scripts/setup.sh
./scripts/dev.sh
```

Keep the server terminal open. It binds only to localhost:8766, creates an empty persistent KG in `$HOME/labweb-project-data/runtime/` (outside the checkout), and creates a private token file. Set `LABKG_STATE` to override that directory in both launchers. If another server uses 8766, stop that instance or set `LABKG_PORT=8767` when starting this server and `LABKG_URL=http://127.0.0.1:8767` in the MCP launcher environment. Do not connect the launcher to a different instance's token.

Project knowledge lives separately under `$HOME/labweb-project-data/methylation/knowledge/`; the runtime KG can serve multiple projects.

For an existing `.labkg-dev/` or `~/.local/state/labweb/` installation, stop the HTTP server before moving the entire directory to the new state path. Preserve the database, any SQLite WAL/SHM files, and `agent.token` together. Restart `./scripts/dev.sh` to regenerate `mcp-config.json` with the new token path, then reconnect MCP clients so they read the new path. Do not start a fresh server at the destination before migrating.

## Connect Codex

In a second terminal, from this repository:

```bash
codex mcp add labweb -- "$PWD/scripts/mcp.sh"
codex mcp get labweb
codex
```

This registers a user-level server entry. Reopen an existing Codex session after registration. In Codex desktop, open this folder and check the MCP server settings if the entry is not visible. `AGENTS.md` supplies this project's agent workflow. The registered path is absolute; register again if you move the checkout.

## Connect Claude Code

From this repository:

```bash
claude mcp add --transport stdio --scope local labweb -- "$PWD/scripts/mcp.sh"
claude
```

Use `/mcp` to inspect the connection. `CLAUDE.md` points to the same workflow as `AGENTS.md`. Registration does not supply a model subscription or API credentials; use your existing client login. Both clients use the same server and development identity.

These commands follow the [official Codex MCP documentation](https://developers.openai.com/codex/mcp) and [official Claude Code MCP documentation](https://code.claude.com/docs/en/mcp), and were checked against the installed CLIs. The API is native HTTP; the launcher provides the optional stdio MCP adapter. Do not register the native HTTP URL as a streamable HTTP MCP endpoint.

## Exercise the conversation

Start with a new project ID for each independent initialization (for example `methylation-codex-ux` or `methylation-claude-ux`). Give the agent your original methylation metadata, header/examples and documentation URLs, then ask:

> Initialize project `methylation-codex-ux` from the metadata and documentation below. Discover the server contract first. Keep only manifest/PED paths and schemas, not individual records. Distill the high-level workflows and their source evidence. Compare your draft with the contract, ask me for genuinely missing information, and wait for my answer before submitting if it blocks initialization. Resolve research and technical bookkeeping yourself. Preserve later implementation questions as open issues. Do not read the repository's completed methylation proposal or curated workflow answers for this UX test; derive the proposal from what I supply and the fetched sources.

Paste the metadata after the prompt. To deliberately test clarification, omit the manifest path and explicitly say that the path is unknown and should not be inferred from the repository. The agent should ask for that path. Reply with the real path or explain that you do not yet know it; the agent must not invent one. Another useful case is ambiguous PED column meaning: the agent should flag the ambiguity even when a structurally valid draft is possible.

Expected flow: contract → source reads and distillation → assessment → user clarification if required → reassessment → atomic initialization → retrieval. Do not give the user a JSON authoring assignment. Missing source extraction is agent work, not a question for the user. Missing runtime/raw-file access can remain a validation limitation.

After initialization, ask:

> Retrieve the context needed to begin generalizing the trio Nextflow pipeline. Identify the existing implementation, the proposed changes and unresolved decisions. Do not modify Tapestry yet.

Then ask the agent to record one agreed decision with `record_work`. Open the other client against the same server and ask it to retrieve that decision and the project context. This checks whether memory survives a client switch. Same-ID identical initialization retries should be harmless; a conflicting replacement should fail clearly. The `project_context` receipt captures initialization; later work events are retrieved through `recall`.

## What to evaluate

- Does it ask only questions you can answer, without repeating supplied information?
- Does it wait for required answers and explain why they are needed?
- Are file schemas correct, and workflow claims backed by accurate source spans?
- Does it distinguish implemented, planned and unknown behavior?
- Can the other client recover the result and the recorded decision?
- Does the KG omit individual PED/manifest records?

Do not consider a replay of the supplied example bundle a test of fresh model distillation. The automated suite checks server/protocol behavior; conversational quality in either client is yours to assess here. There is no background LLM worker or automatic capture of all agent activity. The agent must emit useful summaries with `record_work`.

## Fresh state and checks

To repeat from an empty KG, stop the server and preserve the old state by choosing a new directory:

```bash
LABKG_STATE="$HOME/labweb-project-data/runtime-second" ./scripts/dev.sh
```

Register a separate MCP entry with `LABKG_STATE` passed to the launcher using your client's `--env` option. Keep server and launcher state paths identical. Using new project IDs in the existing KG is simpler when isolation is unnecessary. State directories and tokens are ignored by Git.

Run the automated suite with `.venv/bin/python -m pytest tests -q`. Tests use synthetic fixtures. Project-specific replay tools and completed proposals belong in an external project-data directory and are not part of a fresh conversational UX test. See `examples/README.md` for the generic integration demonstrations. Real-data validation and production hosting remain separate work.

## Remote evidence viewer

See [EVIDENCE_VIEWER.md](EVIDENCE_VIEWER.md) for architecture and compatibility limits.
After updating/restarting the HTTP service and MCP bridge, ask:

> Use graph_view with project_id methylation-codex-ux, query HiFi Tapestry, and depth 2.

In an MCP Apps-capable client, the graph should appear without local renderer
commands. Select a relationship and verify the source quotation/revision, filter
relationships, and expand a node. Confirm omission counts appear when limits are
small. The authenticated browser fallback is http://127.0.0.1:8766/viewer.
Use a reader token; do not paste credentials into chat or URLs.

The UI receives a versioned subgraph and only uses maintained components. It
must never execute HTML/JavaScript contained in source evidence. The A2UI adapter
currently supports only the published fixed composition, not arbitrary screens.
Run `npm run build:ui` and `npm run test:ui` after UI changes in addition to pytest.
