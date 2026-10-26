# Viewer source and test harness

- `src/graph.js`: transport-independent Cytoscape.js EvidenceGraph and EvidencePanel components.
- `src/a2ui.js`: bounded A2UI v0.9.1 composition adapter for the published custom catalog.
- `src/main.js`: MCP Apps SDK adapter and browser fallback.
- `build.mjs`: produces the self-contained, checked-in `labkg/app.html` resource.
- `test_server.py`, `tests/`: synthetic fixtures and browser/protocol tests only.

Public component callbacks are `select({kind: 'node'|'edge', id})` and
`expand(nodeId)`. Selection is local UI state and does not imply a scientific
assertion or write to the KG. Expansion requests another bounded server subgraph.
No component receives credentials. The browser adapter alone holds its reader
token in memory; MCP Apps use the host bridge instead.

The A2UI adapter supports one complete createSurface/updateComponents/
updateDataModel batch and the catalog in `labkg/a2ui.catalog.json`. The agent
selects EvidenceGraph, EvidencePanel, or both in display order through the
`graph_view` components argument. Evidence-only views include an item picker.
Incremental updates, arbitrary layouts and native third-party renderer
registration are future work; these limitations do not affect the independent graph data API.
The composition adapter validates before replacing the visible surface.

The bundled MCP Apps SDK is pinned in package-lock.json. Its dependency licenses
are included in `labkg/third-party-licenses.txt`. Rebuild with `npm run build:ui`.
