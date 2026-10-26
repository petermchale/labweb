# Remote evidence viewer

The viewer has three boundaries:

1. `labkg/graph.py` retrieves an active-revision subgraph. It does not generate UI code.
2. `ui/src/graph.js` uses pinned Cytoscape.js and its Dagre extension for graph layout, pan/zoom, dragging and selection, alongside the evidence panel. It has no HTTP or MCP dependency.
3. `ui/src/main.js` handles MCP Apps or browser authentication and graph requests.

`ui/src/a2ui.js` composes the graph and evidence panel using a deliberately small
A2UI v0.9.1 catalog adapter. This is a prototype of the fixed Column + EvidenceGraph
+ EvidencePanel composition, not a general-purpose A2UI interpreter. It rejects
unknown components, bindings and catalogs. A full native A2UI client still needs
the Labweb custom components registered. Graph retrieval does not depend on A2UI.

## Data API

`POST /view` and MCP `graph_view` now return `labkg.graph/v2`, defined in
`labkg/graph.schema.json`. Only v2 contracts are supported; regenerate saved v1
graph data through `graph_view` before rendering it.

Example tool arguments (no individual records required):

```json
{"query":"HiFi Tapestry", "project_id":"methylation-codex-ux", "depth":2}
```

Use a returned node's exact ID as `focus` to select its neighborhood. Expansion
replaces the current view; it is not an unbounded merge. `depth` is 0–3,
`max_nodes` is 1–100, and `max_edges` is 1–200. `predicates` selects supported
relationship names (`input`, `output`, `dependsOn`, `hasStep`, `uses`, `mentions`,
`imports`, `defines`, `father`, `mother`, `sample`, `family`).

Nodes are IRIs; literals, types and source pointers are node properties. Every
edge/property carries its assertion ID, source, revision, line, quotation,
extraction method and evidence status. The response's `scope` reports query,
project filter, seeds, depth, limits, selection policy and omitted counts.
Limits are relative to the selected neighborhood, not the entire KG.
Lexical seeds are chosen from identifiers and labels; this is not semantic search.
An explicit project ID with an empty query starts from workflow nodes.

Authentication currently grants access to the whole store. A project filter is
**not** a per-project permission boundary. Graph retrieval uses the same bearer
authentication as recall. It materializes the active RDF dataset and is intended
for the current small-server deployment, not large graph serving.

## Remote delivery

`graph_view` advertises `_meta.ui.resourceUri=ui://labweb/evidence-graph/v2`.
The MCP bridge retrieves the maintained self-contained app from the remote
Labweb `/ui/resource` endpoint. No client checkout, local renderer command,
model-authored JavaScript, or CDN access is needed. The resource uses
`text/html;profile=mcp-app`; its CSP metadata grants no external resource or
connection domains. Expansion goes through the host's MCP `tools/call` bridge.
The MCP Apps SDK is bundled at build time and credentials are never embedded.

The existing deployment still uses a stdio MCP bridge configured with
`LABKG_URL` and a token for the remote HTTP service. This change does not add
an unauthenticated Streamable HTTP MCP endpoint or change deployment/auth setup.
Install the Python package for the bridge rather than requiring a source checkout.
Client MCP Apps support must be tested in each actual target client. Unsupported
clients still receive structured graph data and can summarize it.

On the first graph result, the app requests `fullscreen` through the MCP Apps
bridge if the host advertises that display mode. This makes the viewer visible
in the host's app panel instead of relying on an inline tool result that may be
collapsed. Hosts that decline or support only inline mode retain the inline view;
neighborhood updates do not repeatedly request a display-mode change.

Desktop verification (2026-10-26): the configured stdio bridge served its HTML
resource successfully, and the native app panel displayed the five-node HiFi
WDL/miniwdl-output/Tapestry handoff. Selecting an input relationship displayed
its quotation, source line and revision. Earlier empty computer-use app-tab
inventories were not evidence of failed launch: that inventory excludes inline
apps. Desktop logs confirmed the earlier inline iframe initialized and ran
Cytoscape. Use the actual app panel and resource/initialization logs for diagnosis.

The browser fallback is `/viewer`. Its public shell contains no graph data.
Enter a reader token, project and query; the token remains in page memory only,
and `/view` authenticates every request. Serve through HTTPS outside localhost.
Use a read-only token. The page does not persist credentials in URLs or storage.

`POST /view/a2ui` returns a three-message `application/a2ui+json` stream: create
surface, define components, populate the graph model. Catalog identity is
`urn:labweb:a2ui:catalog:v1`. The same composition is used inside the MCP App.
Selection updates the evidence panel locally; expansion invokes the host adapter.

## Build and verify

The packaged `labkg/app.html` includes all runtime code and styles. Rebuild after
editing UI sources:

```bash
npm ci --ignore-scripts
npm run build:ui
.venv/bin/python -m pytest tests -q
npm run test:ui
```

Browser tests use installed Chrome by default and a temporary synthetic-only
HTTP server at localhost:8779. They exercise the packaged artifact, browser token
flow, graph filtering, evidence selection and MCP initialization/tool-result/
expansion messages through a simulated sandbox host. They do not prove support
in a particular commercial client. No real manifest/PED data is used.

Manual acceptance: connect a clean MCP Apps-capable client to the bridge, call
`graph_view`, select a handoff edge, inspect its exact source/revision, expand a
node, and verify that truncation and errors are visible. Repeat with a reader
credential, empty query result, missing focus and a narrow viewport. Confirm no
local Labweb files or external CDN requests are needed by the UI.
