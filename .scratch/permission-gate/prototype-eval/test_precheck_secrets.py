"""Ticket 06 requirement: unit-test the literal-secret rules with FAKE tokens (built from parts at runtime).

Run: python3 -m pytest -q .scratch/permission-gate/prototype-eval/test_precheck_secrets.py
"""
import precheck as p

FAKE_ANTHROPIC = "sk-ant-" + "a1B2c3D4" * 4
FAKE_GITHUB = "ghp_" + "Z9y8X7w6" * 4
FAKE_AWS = "AKIA" + "ABCDEFGHIJKLMNOP"
FAKE_JWT = "eyJ" + "hbGciOiJI" + "." + "eyJzdWIiOiIx" + "MjM0" + "." + "abcDEF123456ghi"


def test_known_token_prefixes_escalate():
    for tok in (FAKE_ANTHROPIC, FAKE_GITHUB, FAKE_AWS):
        assert "known token prefix" in p.literal_secret(f"curl -s https://api.example.com -d key={tok}")


def test_jwt_and_bearer_literals_escalate():
    assert "jwt" in p.literal_secret(f"echo {FAKE_JWT}")
    assert p.literal_secret('curl -H "Authorization: Bearer ' + "x" * 20 + '" https://api.example.com')


def test_url_credentials_and_private_key_block_escalate():
    assert "url credentials" in p.literal_secret("git clone https://user:hunter2@example.com/repo.git")
    assert "private key block" in p.literal_secret("-----BEGIN " + "PRIVATE KEY-----\nabc\n-----END " + "PRIVATE KEY-----")


def test_secret_named_assignment_and_flag_with_literal_value_escalate():
    assert p.literal_secret("export API_TOKEN=abc123def456")
    assert p.literal_secret("mysql --password=abc123")
    assert p.literal_secret("curl --password hunter2 https://example.com")


def test_variable_references_are_not_literals():
    assert not p.literal_secret('curl -H "Authorization: Bearer $TOKEN" https://api.example.com')
    assert not p.literal_secret("export API_TOKEN=$OTHER_TOKEN")
    assert not p.literal_secret('KEY="$HOME/key.txt" ls')


def test_keychain_lookup_does_not_trip_the_secret_flag_rule():
    """The false positive found in ticket 11: '-password -s' inside 'find-generic-password'."""
    assert not p.literal_secret('security find-generic-password -s example-service -w')
    assert "keychain read" in p.secret_printing('security find-generic-password -s example-service -w')


def test_identifier_like_long_strings_do_not_escalate():
    assert not p.literal_secret("ls /private/tmp/claude-501/-Users-x-Projects/04ca5e08-5200-4e6d-a5e2-14a8dfba075d/scratchpad")
    assert not p.literal_secret("git show " + "a" * 40)
    assert not p.literal_secret("open file_with_a_very_long_snake_case_name_abcdefghijklmnop123.txt")


def test_secret_printing_rules():
    assert "private key read" in p.secret_printing("cat ~/.ssh/id_rsa")
    assert not p.secret_printing("cat ~/.ssh/id_rsa.pub")
    assert not p.secret_printing("cat ~/.ssh/config")
    assert "environment dump" in p.secret_printing("printenv")
    assert not p.secret_printing("printenv HOME")
    assert not p.secret_printing("env | grep -i token")
    assert ".env contents" in p.secret_printing("cat .env")
    assert not p.secret_printing("cat .env.example")
    assert not p.secret_printing("ls -la .env")


def test_agent_configuration_commands_escalate_locally():
    """Decision Q40 (ticket 06): adding a plugin, marketplace or MCP server always escalates."""
    for cmd in ("claude plugin install typesafe@typesafe-ai", "claude plugin marketplace add example/skills", "claude mcp add example -- npx server"):
        assert p.precheck("Bash", cmd) and p.precheck("Bash", cmd)[0] == "agent configuration command"
    assert not p.precheck("Bash", "claude plugin list")
    assert not p.precheck("Bash", "claude --version")


def test_documentation_heredocs_do_not_trip_command_rules_but_secrets_still_do():
    doc = "cat >> NOTES.md <<'EOF'\nRun `claude plugin install x` and `rm -rf ~` and `cat ~/.ssh/id_rsa` and sudo.\nEOF"
    assert not p.precheck("Bash", doc)
    assert p.precheck("Bash", doc.replace("Run", "export API_TOKEN=abc123def456 Run"))  # a literal secret is still caught
    piped = "cat <<'EOF' | bash\nsudo rm -rf ~\nEOF"
    assert p.precheck("Bash", piped)  # a heredoc feeding a shell is still scanned
