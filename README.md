# homelab-agents

Declarative definition of a Paperclip agent team. Kept separate from the infra repos so it can be deployed
anywhere (a VM, another machine) and reused for other contexts.

```
terraform/   Proxmox VM for Paperclip (bpg/proxmox, HCP Terraform state)
ansible/     configures the VM: Paperclip, systemd, Tailscale, apply.py
paperclip/   the agent team definition (below)
```

```
paperclip/agents/<name>/agent.json   model, role, limits, allowed tools
paperclip/agents/<name>/AGENTS.md    role instructions, with {{CONTEXT}} {{RULES}} {{MISSING_INFO}} placeholders
paperclip/company/context.md         what the team manages (swap this to reuse the team elsewhere)
paperclip/shared/                    rules and "ask for missing info" shared by all specialists
paperclip/apply.py                   idempotent: hire missing agents, fix drift in config and instructions
```

```
PAPERCLIP_COMPANY="homelab.luisbrancher.dev" paperclip/apply.py --check   # dry run
PAPERCLIP_COMPANY="homelab.luisbrancher.dev" paperclip/apply.py           # apply
```

Team (works only on tickets you assign; no heartbeat/schedules): **Chief of staff** (Haiku, routes and reports), **SRE** (Sonnet: incidents, k3s, observability,
storage and backups; read-only `kubectl`), **Platform** (Sonnet: Terraform/Ansible/Helm/ArgoCD, upgrades and their risk), **Security** (Sonnet: exposure, firewall, TLS, CVEs).

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

## Ansible (configure the VM)

`ansible/playbooks/paperclip.yml` (modeled on homelab-infra) sets up: qemu-guest-agent, user `paperclip`, Node 24 (NodeSource),
Claude Code CLI, Paperclip (`onboard --bind lan` + systemd service on :3100), this repo, `paperclip/apply.py`, Node Exporter.

Manual steps are listed in the step by step below (Claude Code login is interactive).

### Vault (Tailscale auth key)

`ansible/group_vars/all/vault.yml` holds `tailscale_auth_key` (Ansible Vault, same format as homelab-infra).
Generate a reusable auth key in the Tailscale admin (Settings, Keys), then:

```
cd ansible
ansible-vault create group_vars/all/vault.yml     # content: tailscale_auth_key: "tskey-auth-..."
```

After Tailscale is up, set `paperclip_bind: tailnet` in `group_vars/all/vars.yml` to expose Paperclip only on the tailnet (requires re-onboarding).

## Step by step

1. **HCP Terraform**: create the CLI-driven workspace `homelab-paperclip-agents` in org `lfck` and attach the variable set
   `proxmox-homelab` (`pm_api_url`, `pm_api_token_id`, `pm_api_token_secret` sensitive, `ssh_public_key`).
   Use the same execution mode as the homelab-infra workspace.
2. **Proxmox**: make sure the Debian 13 cloud-init template `9000` (with qemu-guest-agent) exists on node `pve` and the API token has permissions.
   Check the token: `curl -k -H "Authorization: PVEAPIToken=<id>=<secret>" https://<proxmox>:8006/api2/json/version`.
3. **VM**: `cd terraform && terraform login && terraform init && terraform apply`, then `terraform output ip_paperclip`.
4. **Fixed IP**: DHCP reservation for the VM's MAC in OPNsense (or set `paperclip_ipv4`/`paperclip_gateway`), then set the IP in `ansible/inventory.ini`.
5. **Tailscale key**: create the vault file as described in the Vault section above.
6. **Ansible**: `cd ansible && ansible-galaxy collection install -r requirements.yml && ansible-playbook site.yml --ask-vault-pass`.
   The first run installs everything and stops short of `apply.py`, printing what is missing.
7. **Claude Code login** (once, interactive): `ssh debian@<ip>` then `sudo -iu paperclip claude login`.
8. **Paperclip company**: open `http://<ip>:3100`, finish onboarding and create the company named in `paperclip_company`.
9. **Read-only kubeconfig for the SRE agent** (once): on k3s-node apply `ansible/files/sre-readonly-rbac.yaml`
   (ServiceAccount bound to the built-in `view` role, which cannot read Secrets), then build a kubeconfig from its token and put it on the VM as `/home/paperclip/.kube/config` (mode 600):
   ```
   # on k3s-node
   sudo k3s kubectl apply -f sre-readonly-rbac.yaml
   TOKEN=$(sudo k3s kubectl -n kube-system get secret paperclip-sre-token -o jsonpath='{.data.token}' | base64 -d)
   CA=$(sudo k3s kubectl -n kube-system get secret paperclip-sre-token -o jsonpath='{.data.ca\.crt}')
   cat > kubeconfig <<EOF2
   apiVersion: v1
   kind: Config
   clusters: [{name: k3s, cluster: {server: "https://10.10.10.11:6443", certificate-authority-data: "$CA"}}]
   users: [{name: paperclip-sre, user: {token: "$TOKEN"}}]
   contexts: [{name: k3s, context: {cluster: k3s, user: paperclip-sre}}]
   current-context: k3s
   EOF2
   ```
   Then `scp` it to the VM and check with `sudo -iu paperclip kubectl get nodes`. The Ansible run also clones homelab-infra/gitops/network into `~/homelab`
   (a private repo needs a read-only deploy key; the playbook warns if a clone fails).
10. **Hire the agents**: re-run `ansible-playbook site.yml --ask-vault-pass`; `apply.py` now runs.
11. **Optional**: once Tailscale is up, set `paperclip_bind: tailnet` in `ansible/group_vars/all/vars.yml` (requires re-onboarding).

To change agents later: edit `paperclip/`, merge to `main`, re-run step 10 (the playbook pulls this repo and `apply.py` fixes drift).
