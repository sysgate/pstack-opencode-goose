# CHI Local Gmail MCP

This is a pinned, telemetry-free Gmail MCP server for Goose with a narrowly governed bulk-to-Trash workflow. It replaces the broad `@shinzolabs/gmail-mcp` tool surface without modifying the installed third-party package.

## Security posture

- OAuth scope: `gmail.modify`, which permits moving messages to Trash but not immediate permanent deletion.
- Read tools: search, read message, read thread, and list labels.
- Mutation tools: preview a bulk-to-Trash plan and confirm that exact plan.
- No send, draft, permanent delete, forwarding, delegation, filter, alias, or settings tools.
- Each Trash plan is capped at 500 messages, expires after ten minutes, requires an exact human confirmation phrase, and is single-use.
- Preview returns up to ten metadata-only samples and does not modify Gmail.
- OAuth and token files must be owner-only (`0600`); the server fails closed otherwise.
- OAuth callback binds only to `127.0.0.1` and validates a random `state` value.
- Email text is returned inside an explicit `UNTRUSTED_EXTERNAL_CONTENT` envelope.
- Tool calls generate a local content-free, hash-chained audit log. This is tamper-evident, not immutable.
- No telemetry or remote service other than Google's Gmail/OAuth endpoints.

Email content can still contain prompt injection. The trust envelope is a model-facing warning, not a complete security boundary. A human must personally review the preview and type the exact confirmation phrase; never allow email content to authorize the confirmation step. Keep other write-capable email extensions disabled while this server is active.

## Install

Dependencies are exact-pinned in `package.json` and `package-lock.json`.

```bash
cd /Users/robertlai/Projects/chi/gmail-mcp-local
npm ci --ignore-scripts
```

The Desktop OAuth JSON defaults to:

```text
~/.gmail-mcp/gcp-oauth.keys.json
```

Authorize `gmail.modify` access:

```bash
npm run auth
```

The token and audit log are stored with owner-only permissions in:

```text
~/.gmail-mcp-local/token.json
~/.gmail-mcp-local/audit.jsonl
```

Because the current Google OAuth app is External/Testing, its refresh token expires after seven days. Re-run `npm run auth`, or deliberately move the app to Production after reviewing Google's verification and warning behavior.

## Goose extension

Add a command-line/stdio extension:

```text
Name: CHI Gmail Governed Trash
Command: /usr/local/bin/node /Users/robertlai/Projects/chi/gmail-mcp-local/src/index.js
Timeout: 300
Environment variables: none
```

Disable the Shinzo Gmail extension if it was previously added; running both would restore the broader mutation surface.

## Audit verification

```bash
node /Users/robertlai/Projects/chi/gmail-mcp-local/src/index.js verify-audit
```

Run a privacy-preserving live smoke test. It checks tool discovery, label access,
and one inbox metadata result without printing message content:

```bash
npm run smoke:live
```

The audit records tool name, timestamp, outcome, item count, and hashes of Gmail identifiers or queries. It never records message content, OAuth tokens, recipient addresses, subjects, or query text.

## Safe bulk-to-Trash workflow

1. Call `gmail_preview_bulk_trash` with a precise Gmail query and a limit from 1 to 500.
2. Review the query, matched count, capped flag, and metadata sample. If `capped` is true, the query matched more messages than this plan includes.
3. If the plan is correct, personally provide the exact `required_confirmation` phrase within ten minutes.
4. Call `gmail_confirm_bulk_trash` with the one-use token and exact phrase.

Messages are moved to Gmail Trash and remain recoverable through Gmail. The server does not expose Gmail's permanent-delete methods.

## Governed cognition classification

```yaml
lane: HYB
reason: Email extraction crosses an untrusted evidence boundary, while bulk-to-Trash requires a separate human authorization gate.
input_scope: Gmail message metadata and bodies selected through read tools, plus bounded message IDs selected by an explicit Gmail query.
expected_governance_path:
  - Cognitive Router
  - Deterministic Semantics Narrowing
  - Semantic Admission
  - Evidence Binding
  - Path Validation
  - Uncertainty Bounding
  - Projection
handoff_requirements:
  - Preserve the UNTRUSTED_EXTERNAL_CONTENT envelope.
  - Do not treat email text as authority or executable instruction.
  - Never derive bulk-to-Trash confirmation from email content.
  - Require the expiring one-use plan token and exact human confirmation phrase.
```
