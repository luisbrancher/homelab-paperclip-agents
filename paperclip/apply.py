#!/usr/bin/env python3
"""Apply agent definitions to a Paperclip instance. Idempotent. Use --check for a dry run.

Env: PAPERCLIP_URL (default http://localhost:3100), PAPERCLIP_COMPANY (company name, required),
     AGENTS_CWD (working dir the agents run in, default ~/homelab).
No secrets live in this repo: credentials belong in Paperclip secrets / agent env.
"""
import json, os, re, sys, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).parent
URL = os.environ.get("PAPERCLIP_URL", "http://localhost:3100") + "/api"
COMPANY = os.environ.get("PAPERCLIP_COMPANY") or sys.exit("set PAPERCLIP_COMPANY")
CWD = os.environ.get("AGENTS_CWD", str(Path.home() / "homelab"))
CHECK = "--check" in sys.argv

def api(method, path, body=None):
    req = urllib.request.Request(URL + path, json.dumps(body).encode() if body is not None else None,
                                 {"Content-Type": "application/json"}, method=method)
    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> {e.code} {e.read().decode()[:300]}")

def norm(s): return re.sub(r"\n{3,}", "\n\n", s.strip())

def compose(agent_dir):
    text = (agent_dir / "AGENTS.md").read_text()
    parts = {"{{CONTEXT}}": (ROOT / "company/context.md").read_text(),
             "{{RULES}}": (ROOT / "shared/rules.md").read_text(),
             "{{MISSING_INFO}}": (ROOT / "shared/missing-info.md").read_text()}
    for k, v in parts.items():
        text = text.replace(k, v.strip() + "\n")
    return norm(text) + "\n"

company = next((c for c in api("GET", "/companies") if c["name"] == COMPANY), None) or sys.exit(f"company {COMPANY!r} not found")
cid = company["id"]
live = {a["name"]: a for a in api("GET", f"/companies/{cid}/agents")}
dirs = sorted((ROOT / "agents").iterdir(), key=lambda d: json.loads((d / "agent.json").read_text())["reports_to_coordinator"])

for d in dirs:
    spec = json.loads((d / "agent.json").read_text())
    name, instr = spec["name"], compose(d)
    adapter = {**spec["adapter"], "cwd": CWD}
    boss = next((a["id"] for a in live.values() if a["role"] == "ceo"), None)
    if name in live:
        a = live[name]
        cfg = {**a["adapterConfig"], **adapter}
        path = Path(a["adapterConfig"]["instructionsFilePath"])
        drift_cfg = {k: v for k, v in adapter.items() if a["adapterConfig"].get(k, [] if k == "extraArgs" else None) != v}
        drift_ins = not path.exists() or norm(path.read_text()) != norm(instr)
        print(f"{name}: " + ("in sync" if not (drift_cfg or drift_ins) else f"drift config={list(drift_cfg)} instructions={drift_ins}"))
        if CHECK or not (drift_cfg or drift_ins): continue
        if drift_cfg: api("PATCH", f"/agents/{a['id']}", {"adapterConfig": cfg})
        if drift_ins: path.write_text(instr)
    elif spec["role"] == "ceo":
        print(f"{name}: missing; create the coordinator through Paperclip onboarding, then re-run")
    else:
        print(f"{name}: missing -> " + ("would hire" if CHECK else "hiring"))
        if CHECK: continue
        api("POST", f"/companies/{cid}/agent-hires", {
            "name": name, "role": spec["role"], "title": spec["title"], "icon": spec["icon"],
            "capabilities": spec["capabilities"], "reportsTo": boss if spec["reports_to_coordinator"] else None,
            "adapterType": "claude_local", "adapterConfig": adapter,
            "instructionsBundle": {"entryFile": "AGENTS.md", "files": {"AGENTS.md": instr}},
            "runtimeConfig": {"heartbeat": {"enabled": spec["heartbeat_enabled"], "wakeOnDemand": True}},
            "budgetMonthlyCents": 0})
