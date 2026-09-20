#!/usr/bin/env python3
"""Ticket 03 diagnostic: WHY do candidates trip redaction, and what is the pool made of? Counts only."""
import collections, json, os, re
import extract_commands as x

rows = [json.loads(l) for l in open(os.path.join(x.DATA, "candidates.jsonl"))]
patterns = {
    "pem": x.PEM, "token_prefix": x.TOKEN_PREFIXES, "jwt": x.JWT, "auth_header": x.AUTH_HEADER,
    "bearer": x.BEARER, "url_creds": x.URL_CREDS, "assign": x.ASSIGN, "secret_flag": x.SECRET_FLAG,
}
# Re-derive from the redacted text: any '<REDACTED' marker kind tells us which rule fired.
kinds = collections.Counter()
for r in rows:
    if not r["secret_hit"]:
        continue
    t = r["text"]
    found = set(re.findall(r"<REDACTED(?::([a-z\-]+))?>", t))
    kinds.update(k or "assign/flag/auth" for k in found)
print("secret_hit rows by redaction marker:", dict(kinds))

first = collections.Counter(r["text"].split()[0] if r["text"].split() else "" for r in rows if r["kind"] == "bash")
print("top first tokens:", dict(first.most_common(15)))
heredoc = sum(1 for r in rows if "<<" in r["text"])
print("rows containing a heredoc (<<):", heredoc)
multi = sum(1 for r in rows if "\n" in r["text"])
print("multi-line rows:", multi)
print("rows > 500 chars:", sum(len(r["text"]) > 500 for r in rows))
print("secret_hit rows that are also heredoc:", sum(1 for r in rows if r["secret_hit"] and "<<" in r["text"]))
print("count==1 rows:", sum(r["count"] == 1 for r in rows), "of", len(rows))
