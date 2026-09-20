import crypto from "node:crypto";
import http from "node:http";
import path from "node:path";

import { google } from "googleapis";
import open from "open";

import {
  DEFAULT_CONFIG_DIR,
  ensurePrivateDirectory,
  readPrivateJson,
  writePrivateJson,
} from "./security.js";

export const MODIFY_SCOPE = "https://www.googleapis.com/auth/gmail.modify";

export function resolvePaths(environment = process.env) {
  const configDirectory = environment.GMAIL_MCP_CONFIG_DIR || DEFAULT_CONFIG_DIR;
  return {
    configDirectory,
    oauthPath:
      environment.GMAIL_OAUTH_PATH ||
      path.join(process.env.HOME, ".gmail-mcp", "gcp-oauth.keys.json"),
    tokenPath: environment.GMAIL_TOKEN_PATH || path.join(configDirectory, "token.json"),
    auditPath: environment.GMAIL_AUDIT_PATH || path.join(configDirectory, "audit.jsonl"),
    authPort: Number(environment.GMAIL_AUTH_PORT || 3000),
  };
}

function installedClient(oauthPath) {
  const parsed = readPrivateJson(oauthPath);
  const credentials = parsed.installed;
  if (!credentials?.client_id || !credentials?.client_secret) {
    throw new Error("OAuth JSON must contain Desktop application credentials under 'installed'.");
  }
  return credentials;
}

export function createOAuthClient(paths, tokenRequired = true) {
  ensurePrivateDirectory(paths.configDirectory);
  const credentials = installedClient(paths.oauthPath);
  const redirectUri = `http://127.0.0.1:${paths.authPort}/oauth2callback`;
  const client = new google.auth.OAuth2(
    credentials.client_id,
    credentials.client_secret,
    redirectUri,
  );
  if (tokenRequired) {
    const token = readPrivateJson(paths.tokenPath);
    client.setCredentials(token);
    client.on("tokens", (newTokens) => {
      const current = readPrivateJson(paths.tokenPath);
      writePrivateJson(paths.tokenPath, { ...current, ...newTokens });
    });
  }
  return client;
}

export async function authorize(paths) {
  const client = createOAuthClient(paths, false);
  const state = crypto.randomBytes(32).toString("hex");
  const authorizationUrl = client.generateAuthUrl({
    access_type: "offline",
    prompt: "consent",
    include_granted_scopes: false,
    scope: [MODIFY_SCOPE],
    state,
  });

  const tokens = await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      server.close();
      reject(new Error("OAuth authorization timed out after five minutes."));
    }, 300_000);

    const server = http.createServer(async (request, response) => {
      try {
        const url = new URL(request.url ?? "/", `http://127.0.0.1:${paths.authPort}`);
        if (url.pathname !== "/oauth2callback") {
          response.writeHead(404).end("Not found");
          return;
        }
        if (url.searchParams.get("state") !== state) {
          response.writeHead(400).end("Invalid OAuth state");
          throw new Error("OAuth state validation failed.");
        }
        const code = url.searchParams.get("code");
        if (!code) throw new Error("Google did not return an authorization code.");
        const result = await client.getToken(code);
        response
          .writeHead(200, { "Content-Type": "text/plain; charset=utf-8" })
          .end("Gmail modify authorization succeeded. You may close this window.");
        clearTimeout(timeout);
        server.close();
        resolve(result.tokens);
      } catch (error) {
        clearTimeout(timeout);
        server.close();
        reject(error);
      }
    });

    server.on("error", reject);
    server.listen(paths.authPort, "127.0.0.1", () => {
      process.stderr.write(`Open this Google authorization URL if the browser does not open:\n${authorizationUrl}\n`);
      open(authorizationUrl).catch(() => undefined);
    });
  });

  writePrivateJson(paths.tokenPath, tokens);
  return paths.tokenPath;
}
