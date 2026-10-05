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

## Terraform (dedicated Proxmox VM)

`terraform/` provisions the VM that runs Paperclip, modeled on [homelab-infra](https://github.com/luisbrancher/homelab-infra)
(same `bpg/proxmox` provider, same variables, clone of the Debian 13 cloud-init template `9000`, SSH key via cloud-init).

- VM `paperclip`, id 110 (k3s-node is 100, lxc-monitoring is 120), 4 cores, 8GB RAM, 60GB on `local-lvm`; all overridable in `variables.tf`.
- IP is DHCP by default; set `paperclip_ipv4` + `paperclip_gateway` for a static one.
- State lives in HCP Terraform (org `lfck`, workspace `homelab-paperclip-agents`). Create the workspace and set the same
  sensitive variables as homelab-infra: `pm_api_url`, `pm_api_token_id`, `pm_api_token_secret`, `ssh_public_key`.

```
cd terraform && terraform init && terraform plan && terraform apply
terraform output ip_paperclip
```

Installing Paperclip itself and running `apply.py` on the VM is the next step (Ansible, in homelab-infra's style).
