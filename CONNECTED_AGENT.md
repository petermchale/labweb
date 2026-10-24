# Initialize the KG by talking to a connected agent

The connected agent now has a complete initialization path. You can supply the methylation metadata in ordinary language—including the header/example needed to infer a schema and the gist/AGENTS.md URLs—and ask the agent to initialize the project. You do not need to write the contracts or run the case-study seed script.

The agent derives the project-specific file schemas and workflow descriptions. The server supplies only the generic initialization format and workflow vocabulary. It fetches source snapshots, verifies citation hashes and exact line spans, validates the proposed records, and commits the project atomically. This is agent-side distillation with deterministic server validation, not an autonomous server-side LLM.

## Start the dev server

From this package, after installing it as described in README.md:

```bash
python examples/dev_server.py --state .labkg-dev --port 8766
```

This creates a local persistent database, a private token file and `.labkg-dev/mcp-config.json`. Register the `labkg` entry from that file with your MCP-capable agent client. It launches `python -m labkg.mcp_server` with the server URL and token-file path. The configuration contains no token value. Client configuration formats differ; the generated file uses the common `mcpServers` JSON shape. Registration in your agent application is still a connection/setup step, not something this server can do by itself.

For this checkout, start `./scripts/dev.sh`; state and generated connection configuration are in `.labkg-dev/`. See [client-specific setup and UX tests](docs/UX_TESTING.md). Runtime databases and credentials are not committed. The historical reports describe the separate development instance used to verify this implementation.

## What you tell the agent

> Initialize a methylation project in the connected KG from this metadata and these documentation links. Retain only manifest/PED file paths and schemas; infer those schemas from the examples and explanations I provide. Distill the high-level WDL, pedigree and trio workflows, with sources and explicit limitations. Do not store individual records. Then retrieve the context needed to start generalizing the generic Nextflow workflow to trios.

Follow that with the original metadata and URLs. The agent calls:

1. `initialization_contract`: discovers the generic envelope, vocabulary and policy.
2. `read_source`: reads documentation and obtains immutable source IDs, hashes and line spans.
3. `assess_initialization`: compares the draft with the server contract, returning user questions separately from agent tasks. Ask unresolved questions in the conversation and wait for answers; reuse information already supplied. Reassess after filling gaps.
4. `initialize_project`: submits its own schemas and source-cited workflow definitions, prose and known gaps.
5. `project_context` / `recall`: retrieves the initialized context for development.

`initialize_project` optionally accepts `validate_only=true` for a dry run. A normal call commits automatically if valid. Identical retries return the original receipt. A conflicting attempt to replace an initialized project is rejected; later work uses explicit incremental ingestion. All writes are attributed to the authenticated agent.

Native HTTP equivalents are `GET /initialization/contract`, `POST /sources/read`, `POST /initialization/assess`, `POST /initialize`, and `GET /projects/{project_id}`. MCP remains optional.

## What was tested

A real MCP client connected to an initially empty dev graph, fetched the pinned Tapestry AGENTS.md and the public gist README, and submitted the distillation authored by this agent from the original user prompt. It initialized two file contracts and six workflows, retrieved the resulting context, and verified safe retry. No seed script populated the dev graph. `examples/connected_initialization_probe.py` is the reproducible transport test; `examples/methylation-initialization.json` is the exact inspectable agent-authored proposal with fetched-source references.

The probe replays that authored proposal—it does not invoke a fresh model to infer schemas. Thus the test proves the connection and initialization machinery, not general model reliability. Source quotation checks establish traceability, not independent scientific validation. The schemas have not been checked against the inaccessible full data files.

47 tests passed, including atomic rejection of incorrect quotations/digests, out-of-project IDs, invalid schemas and raw-row payloads; validation-only calls; restart/replay; concurrent duplicates; source-fetch constraints; and reader/write permissions. Live initialization results are in `reports/connected-initialization.json`.

## Is this enough to begin the trio Nextflow generalization?

Yes. A development server and a populated project context are sufficient to start implementation. Production hosting and autonomous background synthesis are not prerequisites. The context identifies the current pedigree-only generic path, the legacy trio implementation, its phase source, input/output differences and scientific invariants.

The initial development slice should introduce an explicit trio-mode input/output contract, choose model-only versus count-plus-model behavior, and create a small synthetic trio fixture before wiring the trio branch. Preserve the existing pedigree path. In particular, do not treat HiPhase-derived model BEDs as WhatsHap/pedMEC-compatible without regeneration or a validated mapping.

Real-data validation will still require the source files and pipeline runtime where they are available. Missing longitudinal metadata is a separate gap. This change does not claim the trio pipeline has been implemented or that the KG has already been shown to accelerate its implementation.

## Clarification behavior

The server detects structural gaps; the agent must also identify semantic ambiguities and record them in `clarifications` with a question, reason and `required_for` stage. Unanswered initialization questions block submission. Implementation or validation questions remain explicit open issues without blocking a metadata-only KG. Partial assessment drafts are not stored. The server returns questions; the connected agent is responsible for asking them and waiting, never inventing answers or treating silence as an answer.

The live MCP clarification probe omitted a known file path and received a targeted user question; restoring the original user-supplied path made the draft ready. Omitting workflows instead produced an agent task. This tests the protocol, not a new human conversation. See `reports/clarification-check.json`.
