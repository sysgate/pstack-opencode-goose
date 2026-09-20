const SELECTED_HEADERS = ["From", "To", "Cc", "Bcc", "Subject", "Date", "Message-ID"];

export function decodeBase64Url(value = "") {
  if (!value) return "";
  return Buffer.from(value, "base64url").toString("utf8");
}

function collectParts(part, output = []) {
  if (!part) return output;
  output.push(part);
  for (const child of part.parts ?? []) collectParts(child, output);
  return output;
}

function decodeHtmlEntities(value) {
  return value
    .replaceAll("&nbsp;", " ")
    .replaceAll("&amp;", "&")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&quot;", '"')
    .replaceAll("&#39;", "'");
}

export function htmlToPlainText(value) {
  return decodeHtmlEntities(
    value
      .replace(/<script[\s\S]*?<\/script>/gi, " ")
      .replace(/<style[\s\S]*?<\/style>/gi, " ")
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<\/p>/gi, "\n")
      .replace(/<[^>]+>/g, " "),
  )
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function extractBody(payload, maxCharacters = 20_000) {
  const parts = collectParts(payload);
  const plainPart = parts.find(
    (part) => part.mimeType === "text/plain" && part.body?.data,
  );
  const htmlPart = parts.find(
    (part) => part.mimeType === "text/html" && part.body?.data,
  );
  const fallbackPart = payload?.body?.data ? payload : null;
  const selected = plainPart ?? htmlPart ?? fallbackPart;
  if (!selected) return { text: "", truncated: false };
  const decoded = decodeBase64Url(selected.body.data);
  const text = selected.mimeType === "text/html" ? htmlToPlainText(decoded) : decoded;
  return {
    text: text.slice(0, maxCharacters),
    truncated: text.length > maxCharacters,
  };
}

export function selectedHeaders(payload) {
  const headers = new Map(
    (payload?.headers ?? []).map(({ name, value }) => [name.toLowerCase(), value]),
  );
  return Object.fromEntries(
    SELECTED_HEADERS.map((name) => [name.toLowerCase().replace("-", "_"), headers.get(name.toLowerCase()) ?? null]),
  );
}

export function attachmentMetadata(payload) {
  return collectParts(payload)
    .filter((part) => part.filename && part.body?.attachmentId)
    .map((part) => ({
      filename: part.filename,
      mime_type: part.mimeType ?? null,
      size: part.body.size ?? null,
      attachment_id: part.body.attachmentId,
    }));
}

export function safeMessageRecord(message, { includeBody = true, maxBodyCharacters = 20_000 } = {}) {
  const body = includeBody ? extractBody(message.payload, maxBodyCharacters) : null;
  return {
    id: message.id,
    thread_id: message.threadId,
    label_ids: message.labelIds ?? [],
    internal_date: message.internalDate ?? null,
    headers: selectedHeaders(message.payload),
    snippet: (message.snippet ?? "").slice(0, 500),
    body,
    attachments: attachmentMetadata(message.payload),
  };
}
