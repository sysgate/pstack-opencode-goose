"""What leaves the machine and what the log keeps: the same redaction and masking the evaluation used."""
import pytest

import sanitize as s


def test_secret_like_strings_are_redacted_and_emails_masked():
    assert "<REDACTED:token>" in s.redact("curl -H x " + "sk-ant-" + "a1B2c3D4" * 4)
    assert "<REDACTED:jwt>" in s.redact("echo eyJ" + "hbGciOiJI.eyJzdWIiOiIx" + "MjM0.abcDEF123456ghi")
    assert s.redact("export API_TOKEN=abc123def456") == "export API_TOKEN=<REDACTED>"
    redacted = s.redact('curl -H "Authorization: Bearer ' + "x" * 20 + '"')
    assert "<REDACTED>" in redacted and "x" * 20 not in redacted
    assert s.redact("mail -s hi someone@example.com") == "mail -s hi <EMAIL>"
    assert s.redact("export API_TOKEN=$OTHER") == "export API_TOKEN=$OTHER"          # a reference, not a literal


@pytest.mark.parametrize("text", ["git show " + "a" * 40, "ls /tmp/04ca5e08-5200-4e6d-a5e2-14a8dfba075d/x",
                                  "open /Users/x/file_with_a_very_long_snake_case_name_abcdefghijklmnop123.txt", "ls -la"])
def test_identifiers_are_left_alone(text):
    assert s.redact(text) == text


def test_long_mixed_tokens_are_redacted_but_only_as_a_backstop():
    token = "Zx9" + "aB3dE5fG7hJ9kL1mN3pQ5rS7tU9vW1" * 2
    assert s.redact(f"curl -d {token} https://example.com") == "curl -d <REDACTED:long-token> https://example.com"


def test_file_names_under_sensitive_folders_are_masked_and_folders_kept():
    assert s.mask_paths('textutil -convert txt "/Volumes/Vault/Private Memo v2.docx"') == 'textutil -convert txt "/Volumes/Vault/<FILE>.docx"'
    assert s.mask_paths("cat /Users/x/Downloads/Agreement_final.pdf") == "cat /Users/x/Downloads/<FILE>.pdf"
    assert s.mask_paths("ls /Volumes/Vault") == "ls /Volumes/Vault"
    assert s.mask_paths("cat /Users/x/Projects/chi/README.md") == "cat /Users/x/Projects/chi/README.md"


def test_sanitize_is_idempotent():
    text = 'mail x@example.com < "/Users/x/Documents/Plan 2027.xlsx"; export A_TOKEN=abc123def456'
    once = s.sanitize(text)
    assert s.sanitize(once) == once and "Plan 2027" not in once and "x@example.com" not in once


def test_data_heredoc_bodies_become_a_marker_but_interpreter_heredocs_stay():
    doc = "cat >> NOTES.md <<'EOF'\nprivate meeting notes\nmore private text\nEOF\necho done"
    out = s.strip_data_heredocs_marked(doc)
    assert "private" not in out and "[heredoc body omitted: " in out and out.startswith("cat >> NOTES.md <<'EOF'") and out.endswith("EOF\necho done")
    code = "python3 - <<'EOF'\nprint(1)\nEOF"
    assert s.strip_data_heredocs_marked(code) == code


def test_for_jev_bash_strips_sanitizes_and_caps():
    out = s.for_jev_bash("cat >> N.md <<'EOF'\n" + "line\n" * 2000 + "EOF")
    assert len(out) < 200 and "omitted" in out
    assert len(s.for_jev_bash("echo " + "y " * 5000)) == s.MAX_JEV_CHARS


def test_for_jev_mcp_shortens_long_values_but_keeps_every_key():
    out = s.for_jev_mcp({"to": ["a@example.com"], "body": "secret " * 200, "subject": "Hi"})
    assert '"to"' in out and '"subject": "Hi"' in out and "…" in out and len(out) < 400 and "a@example.com" not in out


def test_paths_with_spaces_are_masked_whether_quoted_or_escaped():
    assert "Diary" not in s.mask_paths('cat "/Users/x/Documents/My Diary.txt"')
    assert "Diary" not in s.mask_paths("cat /Users/x/Documents/My\\ Diary.txt && ls")
    assert s.mask_paths("cat /Users/x/Documents/My\\ Diary.txt && ls").endswith("<FILE>.txt && ls")


def test_audit_prefix_is_masked_and_short():
    p = s.prefix('cat   "/Users/x/Documents/My Diary.txt"   && echo ' + "z" * 200)
    assert len(p) <= s.PREFIX_CHARS and "Diary" not in p and p.endswith("…")
