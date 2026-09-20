#!/usr/bin/env node

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const serverPath = new URL("../src/index.js", import.meta.url).pathname;
const transport = new StdioClientTransport({
  command: "/usr/local/bin/node",
  args: [serverPath],
  stderr: "pipe",
});
const client = new Client({ name: "chi-gmail-live-smoke", version: "1.0.0" });

function parseToolPayload(result) {
  if (result.isError) throw new Error("Gmail MCP tool returned an error.");
  const textBlock = result.content.find(({ type }) => type === "text");
  if (!textBlock?.text) throw new Error("Gmail MCP returned no text payload.");
  return JSON.parse(textBlock.text);
}

try {
  await client.connect(transport);
  const listed = await client.listTools();
  const toolNames = listed.tools.map(({ name }) => name).sort();

  const labelsPayload = parseToolPayload(
    await client.callTool({ name: "gmail_list_labels", arguments: {} }),
  );
  const searchPayload = parseToolPayload(
    await client.callTool({
      name: "gmail_search",
      arguments: { query: "in:inbox", max_results: 1 },
    }),
  );
  const previewPayload = parseToolPayload(
    await client.callTool({
      name: "gmail_preview_bulk_trash",
      arguments: {
        query: "rfc822msgid:codex-safe-bulk-trash-smoke-never@invalid.example",
        max_messages: 1,
      },
    }),
  );

  const result = {
    ok: true,
    tools: toolNames,
    governed_bulk_trash_surface:
      toolNames.includes("gmail_preview_bulk_trash") &&
      toolNames.includes("gmail_confirm_bulk_trash"),
    permanent_delete_exposed: toolNames.some((name) => /delete/i.test(name)),
    unrelated_write_tools_exposed: toolNames.some((name) => /send|draft|setting/i.test(name)),
    labels_count: labelsPayload.data.length,
    labels_trust_boundary: labelsPayload.security_boundary?.trust,
    inbox_metadata_results: searchPayload.data.length,
    search_trust_boundary: searchPayload.security_boundary?.trust,
    zero_match_preview_count: previewPayload.matched_count,
    zero_match_preview_created_token: Boolean(previewPayload.confirmation_token),
    message_content_printed: false,
  };
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
} finally {
  await client.close();
}
