# Generic integration examples

- `capture.py` forwards command output into a work-event journal. It does not redact output; use a dedicated stream without credentials or individual records.
- `mcp_probe.py` uses two test credentials to write a unique synthetic marker through one MCP client and retrieve it through another. Run it against a disposable development server with `LABKG_URL` set to that server. The first credential needs write access; the second needs read access.
- `AGENT_INTEGRATION.md` describes how agents retrieve evidence and record work.

The local development server lives in `scripts/dev_server.py`; start it with `./scripts/dev.sh`.

Project-specific experiments, curated answers and completed initialization proposals belong in an external project-data directory. They are not bundled with these examples.
