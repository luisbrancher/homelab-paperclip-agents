#!/usr/bin/env python3
"""Apply agent definitions to a Paperclip instance. Idempotent. Use --check for a dry run.

Env: PAPERCLIP_URL (default http://127.0.0.1:3100), PAPERCLIP_API_KEY (board API key; required unless the
     instance runs in local_trusted/loopback mode), PAPERCLIP_COMPANY (company name, required),
     AGENTS_CWD (working dir the agents run in, default ~/homelab).
No secrets live in this repo: the board key comes from Ansible Vault, credentials belong in Paperclip secrets / agent env.
"""
import json, os, re, sys, urllib.parse, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).parent
URL = os.environ.get("PAPERCLIP_URL", "http://127.0.0.1:3100").rstrip("/") + "/api"
KEY = os.environ.get("PAPERCLIP_API_KEY", "").strip()
COMPANY = os.environ.get("PAPERCLIP_COMPANY") or sys.exit("set PAPERCLIP_COMPANY")
CWD = os.environ.get("AGENTS_CWD", str(Path.home() / "homelab"))
CHECK = "--check" in sys.argv

def api(method, path, body=None):
    headers = {"Content-Type": "application/json", **({"Authorization": f"Bearer {KEY}"} if KEY else {})}
    req = urllib.request.Request(URL + path, json.dumps(body).encode() if body is not None else None, headers, method=method)
    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        hint = " (set PAPERCLIP_API_KEY to a board API key)" if e.code in (401, 403) and not KEY else ""
        sys.exit(f"{method} {path} -> {e.code} {e.read().decode()[:300]}{hint}")

def norm(s): return re.sub(r"\n{3,}", "\n\n", (s or "").strip())

def compose(agent_dir):
    text = (agent_dir / "AGENTS.md").read_text()
    parts = {"{{CONTEXT}}": (ROOT / "company/context.md").read_text(),
             "{{RULES}}": (ROOT / "shared/rules.md").read_text(),
             "{{MISSING_INFO}}": (ROOT / "shared/missing-info.md").read_text()}
    for k, v in parts.items():
        text = text.replace(k, v.strip() + "\n")
    return norm(text) + "\n"

def entry_file(agent_id):
    bundle = api("GET", f"/agents/{agent_id}/instructions-bundle")
    path = bundle.get("entryFile", "AGENTS.md")
    return path, api("GET", f"/agents/{agent_id}/instructions-bundle/file?path={urllib.parse.quote(path)}")

company = next((c for c in api("GET", "/companies") if c["name"] == COMPANY), None) or sys.exit(f"company {COMPANY!r} not found")
cid = company["id"]
live = api("GET", f"/companies/{cid}/agents")
specs = [(d, json.loads((d / "agent.json").read_text())) for d in sorted((ROOT / "agents").iterdir())]
specs.sort(key=lambda s: s[1]["role"] != "ceo")  # chief of staff first: the others report to it

def find_live(spec):
    by_name = next((a for a in live if a["name"] == spec["name"]), None)
    # the chief of staff is created by onboarding under its own name: match it by role
    return by_name or (next((a for a in live if a["role"] == "ceo"), None) if spec["role"] == "ceo" else None)

boss = next((a["id"] for a in live if a["role"] == "ceo"), None)
managed = set()

for d, spec in specs:
    name, instr = spec["name"], compose(d)
    adapter = {**spec["adapter"], "cwd": CWD}
    heartbeat = {"enabled": spec["heartbeat_enabled"], "wakeOnDemand": True}
    reports_to = boss if spec["reports_to_chief_of_staff"] else None
    a = find_live(spec)

    if a is None and spec["role"] == "ceo":
        print(f"{name}: missing; create the chief of staff through Paperclip onboarding, then re-run")
        continue
    if a is None:
        print(f"{name}: missing -> " + ("would hire" if CHECK else "hiring"))
        if CHECK: continue
        api("POST", f"/companies/{cid}/agent-hires", {
            "name": name, "role": spec["role"], "title": spec["title"], "icon": spec["icon"],
            "capabilities": spec["capabilities"], "reportsTo": reports_to,
            "adapterType": "claude_local", "adapterConfig": adapter,
            "instructionsBundle": {"entryFile": "AGENTS.md", "files": {"AGENTS.md": instr}},
            "runtimeConfig": {"heartbeat": heartbeat},
            "budgetMonthlyCents": 0})
        continue

    managed.add(a["id"])
    want = {"name": name, "role": spec["role"], "title": spec["title"], "icon": spec["icon"],
            "capabilities": spec["capabilities"], "reportsTo": reports_to}
    patch = {k: v for k, v in want.items() if a.get(k) != v}
    cfg = a.get("adapterConfig") or {}
    drift_adapter = [k for k, v in adapter.items() if cfg.get(k, [] if k == "extraArgs" else None) != v]
    if drift_adapter:
        patch["adapterConfig"] = adapter  # merged into the live config server-side
    runtime = a.get("runtimeConfig") or {}
    if {**(runtime.get("heartbeat") or {}), **heartbeat} != (runtime.get("heartbeat") or {}):
        patch["runtimeConfig"] = {**runtime, "heartbeat": {**(runtime.get("heartbeat") or {}), **heartbeat}}
    path, current = entry_file(a["id"])
    drift_ins = norm(current.get("content")) != norm(instr)

    fields = [k for k in patch if k != "adapterConfig"] + [f"adapter.{k}" for k in drift_adapter]
    print(f"{name}: " + (f"drift {fields} instructions={drift_ins}" if (patch or drift_ins) else "in sync"))
    if CHECK: continue
    if patch:
        api("PATCH", f"/agents/{a['id']}", patch)
    if drift_ins:
        api("PUT", f"/agents/{a['id']}/instructions-bundle/file",
            {"path": path, "content": instr, "baseRevisionId": (current.get("revision") or {}).get("id")})

for a in live:
    if a["id"] not in managed and a.get("status") != "terminated":
        print(f"{a['name']}: unmanaged (not in paperclip/agents/); remove it in the UI or add it to the repo")
