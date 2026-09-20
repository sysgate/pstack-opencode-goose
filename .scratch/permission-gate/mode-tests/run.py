#!/usr/bin/env python3
"""THROWAWAY runner for ticket 08: headless `claude -p` tests in isolated scratch folders. Harmless commands only."""
import json, os, shutil, subprocess, sys, time
S = os.path.dirname(os.path.abspath(__file__))
MODEL = "claude-haiku-4-5-20251001"

def run(name, folder, hook_mode, permission_mode, command, prompt=None, extra=()):
    cwd = f"{S}/{folder}"
    open(f"{cwd}/hook_mode.txt", "w").write(hook_mode)
    for f in ("hook.log",):
        if os.path.exists(f"{cwd}/{f}"): os.remove(f"{cwd}/{f}")
    shutil.rmtree(f"{cwd}/gate-test-dir", ignore_errors=True)
    prompt = prompt or f"Use the Bash tool to run exactly this command and nothing else: {command}\nThen reply with only the command output, or the single word DENIED if the tool call was not allowed."
    cmd = ["claude", "-p", prompt, "--model", MODEL, "--output-format", "json", "--setting-sources", "project", "--strict-mcp-config",
           "--disable-slash-commands", "--no-session-persistence", "--max-budget-usd", "0.40", "--permission-mode", permission_mode, *extra]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=150, stdin=subprocess.DEVNULL)
        out, err, rc = p.stdout, p.stderr[-300:], p.returncode
    except subprocess.TimeoutExpired:
        out, err, rc = "", "TIMEOUT", -1
    try:
        j = json.loads(out)
    except Exception:
        j = {}
    log = []
    if os.path.exists(f"{cwd}/hook.log"):
        log = [json.loads(l) for l in open(f"{cwd}/hook.log")]
    res = {
        "test": name, "folder": folder, "hook_mode": hook_mode, "permission_mode": permission_mode, "rc": rc, "secs": round(time.time() - t0, 1),
        "denials": len(j.get("permission_denials", []) or []), "result": (j.get("result") or "")[:90].replace("\n", " "),
        "is_error": j.get("is_error"), "cost": j.get("total_cost_usd"), "turns": j.get("num_turns"),
        "hook_calls": len(log), "hook_saw_modes": sorted({str(l["permission_mode"]) for l in log}),
        "hook_agent_ids": sorted({str(l["agent_id"]) for l in log if l.get("agent_id")})[:3], "hook_agent_types": sorted({str(l["agent_type"]) for l in log if l.get("agent_type")}),
        "dir_created": os.path.isdir(f"{cwd}/gate-test-dir"), "stderr": err.strip()[-160:],
    }
    json.dump({"summary": res, "raw": j}, open(f"{S}/runs/{name}.json", "w"), indent=1)
    return res

TESTS = {
  "A1_control_silent_allowrule": lambda: run("A1_control_silent_allowrule", "a", "silent", "default", "echo gate-test"),
  "A2_ask_plus_allowrule": lambda: run("A2_ask_plus_allowrule", "a", "ask", "default", "echo gate-test"),
  "C1_control_silent_norule": lambda: run("C1_control_silent_norule", "c", "silent", "default", "echo gate-test"),
  "C2_ask_norule": lambda: run("C2_ask_norule", "c", "ask", "default", "echo gate-test"),
  "A3_dontAsk_ask": lambda: run("A3_dontAsk_ask", "a", "ask", "dontAsk", "echo gate-test"),
  "A3c_dontAsk_silent": lambda: run("A3c_dontAsk_silent", "a", "silent", "dontAsk", "echo gate-test"),
  "A4_plan_ask": lambda: run("A4_plan_ask", "a", "ask", "plan", "echo gate-test"),
  "A4c_plan_silent": lambda: run("A4c_plan_silent", "a", "silent", "plan", "echo gate-test"),
  "A5c_acceptEdits_silent_mkdir": lambda: run("A5c_acceptEdits_silent_mkdir", "c", "silent", "acceptEdits", "mkdir gate-test-dir"),
  "A5_acceptEdits_ask_mkdir": lambda: run("A5_acceptEdits_ask_mkdir", "c", "ask", "acceptEdits", "mkdir gate-test-dir"),
  "A6c_bypass_silent": lambda: run("A6c_bypass_silent", "c", "silent", "bypassPermissions", "echo gate-test", extra=("--allow-dangerously-skip-permissions",)),
  "A6_bypass_ask": lambda: run("A6_bypass_ask", "c", "ask", "bypassPermissions", "echo gate-test", extra=("--allow-dangerously-skip-permissions",)),
  "A7_auto_ask": lambda: run("A7_auto_ask", "c", "ask", "auto", "echo gate-test"),
  "B1_slow_hook_timeout2_allowrule": lambda: run("B1_slow_hook_timeout2_allowrule", "b", "sleep", "default", "echo gate-test"),
  "S1_subagent_hook_fields": lambda: run("S1_subagent_hook_fields", "a", "silent", "default", "echo gate-test",
      prompt="Use the Agent tool to start a general-purpose subagent. Tell the subagent to use its Bash tool to run exactly: echo gate-test . Then reply with only what the subagent reported."),
}
TESTS.update({
  "D1_control_norule_mkdir_silent": lambda: run("D1_control_norule_mkdir_silent", "c", "silent", "default", "mkdir gate-test-dir"),
  "E0_control_flagallow_mkdir_silent": lambda: run("E0_control_flagallow_mkdir_silent", "c", "silent", "default", "mkdir gate-test-dir", extra=("--settings", f"{S}/allow.json")),
  "E1_flagallow_mkdir_ask": lambda: run("E1_flagallow_mkdir_ask", "c", "ask", "default", "mkdir gate-test-dir", extra=("--settings", f"{S}/allow.json")),
})
if __name__ == "__main__":
    names = sys.argv[1:] or list(TESTS)
    for n in names:
        r = TESTS[n]()
        print(json.dumps(r))
