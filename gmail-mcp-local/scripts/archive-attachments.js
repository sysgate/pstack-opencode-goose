#!/usr/bin/env node
import { createHash } from "node:crypto";
import fs from "node:fs";
import { link, mkdir, readFile, rename, symlink, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

import { google } from "googleapis";

import { createOAuthClient, resolvePaths } from "../src/oauth.js";

const DEFAULT_OUTPUT = path.join(os.homedir(), "Documents", "Archive", "GmailAttachments");
const DEFAULT_QUERY = "has:attachment";

function usage() {
  return `Usage:
  node scripts/archive-attachments.js [options]

Options:
  --query <gmail-query>        Gmail search query. Default: ${DEFAULT_QUERY}
  --output-dir <path>          Archive root. Default: ${DEFAULT_OUTPUT}
  --max-messages <n>           Stop after N messages. Default: all matches
  --page-size <n>              Gmail list page size. Default: 100
  --include-inline             Include inline parts with filenames
  --dry-run                    Scan matching messages, do not download files
  --no-sqlite                  Skip attachments.sqlite generation
  --help                       Show this help

Examples:
  node scripts/archive-attachments.js --query 'from:isc2.org has:attachment'
  node scripts/archive-attachments.js --query 'filename:pdf after:2020/01/01' --max-messages 500
`;
}

function parseArgs(argv) {
  const args = {
    query: DEFAULT_QUERY,
    outputDir: DEFAULT_OUTPUT,
    maxMessages: null,
    pageSize: 100,
    includeInline: false,
    dryRun: false,
    sqlite: true,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--help" || arg === "-h") {
      process.stdout.write(usage());
      process.exit(0);
    } else if (arg === "--query") {
      args.query = argv[++i];
    } else if (arg === "--output-dir") {
      args.outputDir = path.resolve(argv[++i]);
    } else if (arg === "--max-messages") {
      args.maxMessages = Number(argv[++i]);
    } else if (arg === "--page-size") {
      args.pageSize = Number(argv[++i]);
    } else if (arg === "--include-inline") {
      args.includeInline = true;
    } else if (arg === "--dry-run") {
      args.dryRun = true;
    } else if (arg === "--no-sqlite") {
      args.sqlite = false;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  if (!args.query) throw new Error("--query cannot be empty.");
  if (!Number.isInteger(args.pageSize) || args.pageSize < 1 || args.pageSize > 500) {
    throw new Error("--page-size must be an integer from 1 to 500.");
  }
  if (args.maxMessages !== null && (!Number.isInteger(args.maxMessages) || args.maxMessages < 1)) {
    throw new Error("--max-messages must be a positive integer.");
  }
  return args;
}

function headerMap(payload) {
  return new Map((payload?.headers ?? []).map(({ name, value }) => [name.toLowerCase(), value]));
}

function getHeader(headers, name) {
  return headers.get(name.toLowerCase()) ?? "";
}

function collectParts(part, output = []) {
  if (!part) return output;
  output.push(part);
  for (const child of part.parts ?? []) collectParts(child, output);
  return output;
}

function attachmentParts(payload, includeInline) {
  return collectParts(payload).filter((part) => {
    if (!part.filename || !part.body?.attachmentId) return false;
    if (includeInline) return true;
    const disposition = (part.headers ?? []).find((h) => h.name?.toLowerCase() === "content-disposition")?.value ?? "";
    return !/^inline\b/i.test(disposition);
  });
}

function sanitize(value, fallback = "item", maxLength = 120) {
  const cleaned = String(value ?? "")
    .normalize("NFKD")
    .replace(/[^\x20-\x7E]/g, " ")
    .replace(/[\\/:*?"<>|\n\r\t]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^[. ]+|[. ]+$/g, "");
  return (cleaned || fallback).slice(0, maxLength).trim() || fallback;
}

function emailAddress(value) {
  const match = String(value ?? "").match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
  return match ? match[0].toLowerCase() : "";
}

function yyyymm(internalDate, dateHeader) {
  const date = internalDate ? new Date(Number(internalDate)) : new Date(dateHeader);
  if (Number.isNaN(date.getTime())) return { year: "unknown", month: "unknown", iso: "" };
  const year = String(date.getFullYear());
  const month = String(date.getMonth() + 1).padStart(2, "0");
  return { year, month: `${year}-${month}`, iso: date.toISOString() };
}

function classify({ sender, subject, filename, mimeType }) {
  const hay = `${sender} ${subject} ${filename} ${mimeType}`.toLowerCase();
  if (/schwab|fidelity|bank|chase|citi|amex|americanexpress|paypal|vanguard|statement|invoice|tax|1099|w-?2/.test(hay)) {
    return "Finance";
  }
  if (/attorney|law|trust|deed|escrow|mortgage|insurance|docusign|contract|agreement/.test(hay)) {
    return "Legal-Property-Tax";
  }
  if (/medical|doctor|hospital|patient|vitas|mycslink|health|haddy|medicare|questdiagnostics/.test(hay)) {
    return "Health-Family";
  }
  if (/isc2|cissp|ccsp|certification|certificate|credential|exam/.test(hay)) {
    return "Professional-Certifications";
  }
  if (/china.*cyber|cyber.*china|cyber warfare|space and cyber space|apt1/.test(hay)) {
    return "Strategic-Cyber-Research";
  }
  if (/paper|capstone|assignment|essay|draft|presentation|course|class|syllabus|transcript|publication/.test(hay)) {
    return "Learning-Presentations";
  }
  if (/saic|aero\.org|booz|bah|nasa|nsa\.gov|project|resume|interview|clearance/.test(hay)) {
    return "Work-Career-Projects";
  }
  if (/trip|flight|hotel|reservation|itinerary|marriott|united|delta|cathay/.test(hay)) {
    return "Life-Events-Travel";
  }
  if (/article|research|reference|report|pdf|docx|pptx|xlsx/.test(hay)) {
    return "Research-Reference";
  }
  return "Needs-Review";
}

async function loadHashIndex(indexPath) {
  try {
    return new Map(Object.entries(JSON.parse(await readFile(indexPath, "utf8"))));
  } catch {
    return new Map();
  }
}

async function atomicWriteJson(filePath, value) {
  await mkdir(path.dirname(filePath), { recursive: true });
  const tempPath = `${filePath}.tmp-${process.pid}`;
  await writeFile(tempPath, JSON.stringify(value, null, 2) + "\n", "utf8");
  await rename(tempPath, filePath);
}

async function materializeLink(blobPath, targetPath) {
  if (fs.existsSync(targetPath)) return;
  try {
    await link(blobPath, targetPath);
  } catch {
    try {
      await symlink(blobPath, targetPath);
    } catch {
      await writeFile(targetPath, await readFile(blobPath));
    }
  }
}

function csvEscapeRows(rows) {
  const headers = Object.keys(rows[0] ?? { ok: "" });
  const escape = (value) => {
    const text = String(value ?? "");
    return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  };
  return [
    headers.map(escape).join(","),
    ...rows.map((row) => headers.map((header) => escape(row[header])).join(",")),
  ].join("\n") + "\n";
}

function writeSqliteFromJsonl(jsonlPath, sqlitePath) {
  const code = String.raw`
import json, sqlite3, sys
from pathlib import Path
jsonl_path = Path(sys.argv[1])
sqlite_path = Path(sys.argv[2])
sqlite_path.parent.mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect(sqlite_path)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS attachments (
  gmail_message_id TEXT,
  gmail_thread_id TEXT,
  attachment_id TEXT,
  sha256 TEXT,
  duplicate_of_sha256 TEXT,
  filename TEXT,
  mime_type TEXT,
  size_bytes INTEGER,
  sender TEXT,
  subject TEXT,
  date_iso TEXT,
  gmail_query TEXT,
  catalog TEXT,
  blob_path TEXT,
  message_folder TEXT,
  materialized_path TEXT,
  message_json_path TEXT,
  message_md_path TEXT,
  archived_at TEXT,
  PRIMARY KEY (gmail_message_id, attachment_id, sha256)
)
""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_attachments_sha256 ON attachments(sha256)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_attachments_sender ON attachments(sender)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_attachments_catalog ON attachments(catalog)")
for line in jsonl_path.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    row = json.loads(line)
    cur.execute("""
    INSERT OR REPLACE INTO attachments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        row.get("gmail_message_id"),
        row.get("gmail_thread_id"),
        row.get("attachment_id"),
        row.get("sha256"),
        row.get("duplicate_of_sha256"),
        row.get("filename"),
        row.get("mime_type"),
        row.get("size_bytes"),
        row.get("sender"),
        row.get("subject"),
        row.get("date_iso"),
        row.get("gmail_query"),
        row.get("catalog"),
        row.get("blob_path"),
        row.get("message_folder"),
        row.get("materialized_path"),
        row.get("message_json_path"),
        row.get("message_md_path"),
        row.get("archived_at"),
    ))
conn.commit()
conn.close()
`;
  const result = spawnSync("python3", ["-c", code, jsonlPath, sqlitePath], { encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(`SQLite generation failed: ${result.stderr || result.stdout}`);
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const auth = createOAuthClient(resolvePaths());
  const gmail = google.gmail({ version: "v1", auth });
  const archiveRoot = args.outputDir;
  const indexDir = path.join(archiveRoot, "_index");
  const blobsDir = path.join(archiveRoot, "_blobs");
  const hashIndexPath = path.join(indexDir, "sha256-index.json");
  const jsonlPath = path.join(indexDir, "attachments.jsonl");
  const csvPath = path.join(indexDir, "attachments.csv");
  const sqlitePath = path.join(indexDir, "attachments.sqlite");
  const manifestPath = path.join(indexDir, "last-run-summary.json");
  const archivedAt = new Date().toISOString();

  await mkdir(indexDir, { recursive: true });
  await mkdir(blobsDir, { recursive: true });
  const hashIndex = await loadHashIndex(hashIndexPath);
  const jsonl = fs.createWriteStream(jsonlPath, { flags: "a", encoding: "utf8" });
  const rows = [];
  let pageToken;
  let scannedMessages = 0;
  let messagesWithAttachments = 0;
  let attachmentCount = 0;
  let downloadedBytes = 0;
  let dedupedAttachments = 0;

  try {
    do {
      const remaining = args.maxMessages === null ? args.pageSize : Math.min(args.pageSize, args.maxMessages - scannedMessages);
      if (remaining <= 0) break;
      const list = await gmail.users.messages.list({
        userId: "me",
        q: args.query,
        maxResults: remaining,
        pageToken,
      });
      const messages = list.data.messages ?? [];
      pageToken = list.data.nextPageToken;
      if (!messages.length) break;

      for (const listed of messages) {
        if (args.maxMessages !== null && scannedMessages >= args.maxMessages) break;
        scannedMessages += 1;
        const full = await gmail.users.messages.get({
          userId: "me",
          id: listed.id,
          format: "full",
        });
        const message = full.data;
        const headers = headerMap(message.payload);
        const subject = getHeader(headers, "subject");
        const from = getHeader(headers, "from");
        const sender = emailAddress(from) || sanitize(from, "unknown-sender");
        const dateHeader = getHeader(headers, "date");
        const dateInfo = yyyymm(message.internalDate, dateHeader);
        const parts = attachmentParts(message.payload, args.includeInline);
        if (!parts.length) continue;
        messagesWithAttachments += 1;

        const messageFolder = path.join(
          archiveRoot,
          "_messages",
          dateInfo.year,
          dateInfo.month,
          `${message.id}__${sanitize(sender, "sender", 70)}__${sanitize(subject, "subject", 90)}`,
        );
        const messageJsonPath = path.join(messageFolder, "message.json");
        const messageMdPath = path.join(messageFolder, "message.md");
        if (!args.dryRun) await mkdir(messageFolder, { recursive: true });

        const messageRecord = {
          gmail_message_id: message.id,
          gmail_thread_id: message.threadId,
          label_ids: message.labelIds ?? [],
          internal_date: message.internalDate ?? null,
          date_iso: dateInfo.iso,
          headers: {
            from,
            to: getHeader(headers, "to"),
            cc: getHeader(headers, "cc"),
            bcc: getHeader(headers, "bcc"),
            subject,
            date: dateHeader,
            message_id: getHeader(headers, "message-id"),
          },
          snippet: message.snippet ?? "",
          gmail_query: args.query,
          attachment_count: parts.length,
        };
        if (!args.dryRun) {
          await writeFile(messageJsonPath, JSON.stringify(messageRecord, null, 2) + "\n", "utf8");
          await writeFile(
            messageMdPath,
            `---\ngmail_message_id: ${JSON.stringify(message.id)}\ngmail_thread_id: ${JSON.stringify(message.threadId)}\nfrom: ${JSON.stringify(from)}\nsender: ${JSON.stringify(sender)}\nsubject: ${JSON.stringify(subject)}\ndate: ${JSON.stringify(dateInfo.iso || dateHeader)}\ngmail_query: ${JSON.stringify(args.query)}\nattachment_count: ${parts.length}\n---\n\n# ${subject || "(no subject)"}\n\nFrom: ${from}\n\nDate: ${dateInfo.iso || dateHeader}\n\nGmail message ID: ${message.id}\n`,
            "utf8",
          );
        }

        for (const part of parts) {
          attachmentCount += 1;
          const filename = sanitize(part.filename, "attachment", 160);
          const catalog = classify({ sender, subject, filename, mimeType: part.mimeType ?? "" });
          let sha256 = "";
          let blobPath = "";
          let duplicateOfSha256 = "";
          let materializedPath = path.join(messageFolder, filename);
          let sizeBytes = part.body?.size ?? 0;

          if (!args.dryRun) {
            const fetched = await gmail.users.messages.attachments.get({
              userId: "me",
              messageId: message.id,
              id: part.body.attachmentId,
            });
            const bytes = Buffer.from(fetched.data.data ?? "", "base64url");
            sizeBytes = bytes.length;
            sha256 = createHash("sha256").update(bytes).digest("hex");
            const suffix = path.extname(filename);
            blobPath = path.join(blobsDir, sha256.slice(0, 2), `${sha256}${suffix}`);
            const existing = hashIndex.get(sha256);
            if (existing) {
              duplicateOfSha256 = sha256;
              dedupedAttachments += 1;
            } else {
              await mkdir(path.dirname(blobPath), { recursive: true });
              await writeFile(blobPath, bytes);
              hashIndex.set(sha256, blobPath);
              downloadedBytes += bytes.length;
            }

            const catalogFolder = path.join(
              archiveRoot,
              catalog,
              dateInfo.year,
              dateInfo.month,
              `${message.id}__${sanitize(sender, "sender", 70)}__${sanitize(subject, "subject", 90)}`,
            );
            await mkdir(catalogFolder, { recursive: true });
            materializedPath = path.join(catalogFolder, filename);
            await materializeLink(hashIndex.get(sha256), materializedPath);
          }

          const row = {
            gmail_message_id: message.id,
            gmail_thread_id: message.threadId,
            attachment_id: part.body.attachmentId,
            sha256,
            duplicate_of_sha256: duplicateOfSha256,
            filename,
            mime_type: part.mimeType ?? "",
            size_bytes: sizeBytes,
            sender,
            subject,
            date_iso: dateInfo.iso,
            gmail_query: args.query,
            catalog,
            blob_path: blobPath,
            message_folder: messageFolder,
            materialized_path: materializedPath,
            message_json_path: messageJsonPath,
            message_md_path: messageMdPath,
            archived_at: archivedAt,
          };
          rows.push(row);
          if (!args.dryRun) jsonl.write(JSON.stringify(row) + "\n");
        }
      }
      process.stderr.write(`[gmail-attachments] scanned=${scannedMessages} attachments=${attachmentCount}\n`);
    } while (pageToken);
  } finally {
    await new Promise((resolve) => jsonl.end(resolve));
  }

  if (!args.dryRun && rows.length) {
    await writeFile(csvPath, csvEscapeRows(rows), "utf8");
    await atomicWriteJson(hashIndexPath, Object.fromEntries(hashIndex));
    if (args.sqlite) writeSqliteFromJsonl(jsonlPath, sqlitePath);
  }

  const summary = {
    archived_at: archivedAt,
    gmail_query: args.query,
    output_dir: archiveRoot,
    dry_run: args.dryRun,
    scanned_messages: scannedMessages,
    messages_with_attachments: messagesWithAttachments,
    attachments_seen: attachmentCount,
    unique_new_blobs: args.dryRun ? null : attachmentCount - dedupedAttachments,
    deduped_attachments: args.dryRun ? null : dedupedAttachments,
    downloaded_bytes: args.dryRun ? null : downloadedBytes,
    jsonl_index: args.dryRun ? null : jsonlPath,
    csv_index: args.dryRun ? null : csvPath,
    sqlite_index: args.dryRun || !args.sqlite ? null : sqlitePath,
    sha256_index: args.dryRun ? null : hashIndexPath,
  };
  if (!args.dryRun) await atomicWriteJson(manifestPath, summary);
  process.stdout.write(JSON.stringify(summary, null, 2) + "\n");
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exit(1);
});
