#!/usr/bin/env node

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const serverPath = new URL("../src/index.js", import.meta.url).pathname;
const transport = new StdioClientTransport({
  command: "/usr/local/bin/node",
  args: [serverPath],
  stderr: "pipe",
});
const client = new Client({ name: "chi-gmail-list-labels", version: "1.0.0" });

try {
  await client.connect(transport);
  const result = await client.callTool({ name: "gmail_list_labels", arguments: {} });
  if (result.isError) throw new Error("Gmail MCP returned an error.");
  const text = result.content.find(({ type }) => type === "text")?.text;
  const payload = JSON.parse(text);
  process.stdout.write(`${JSON.stringify(payload.data, null, 2)}\n`);
} finally {
  await client.close();
}
