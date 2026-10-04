# homelab-agents

Declarative definition of a Paperclip agent team. Kept separate from the infra repos so it can be deployed
anywhere (a VM, another machine) and reused for other contexts.

```
agents/<name>/agent.json   model, role, limits, allowed tools
agents/<name>/AGENTS.md    role instructions, with {{CONTEXT}} {{RULES}} {{MISSING_INFO}} placeholders
company/context.md         what the team manages (swap this to reuse the team elsewhere)
shared/                    rules and "ask for missing info" shared by all specialists
apply.py                   idempotent: hire missing agents, fix drift in config and instructions
```

```
PAPERCLIP_COMPANY="homelab.luisbrancher.dev" ./apply.py --check   # dry run
PAPERCLIP_COMPANY="homelab.luisbrancher.dev" ./apply.py           # apply
```

Rules: no secrets in this repo (use Paperclip secrets / agent env); agents are read-only until their access task is done.
Coordinator is created by Paperclip onboarding; `apply.py` only syncs it.
