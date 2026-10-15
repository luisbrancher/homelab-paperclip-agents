# homelab-paperclip-agents

The Paperclip agent team for homelab.luisbrancher.dev, plus the VM it runs on.

```
terraform/   Proxmox VM for Paperclip (bpg/proxmox, HCP Terraform state)
ansible/     configures the VM: egress filter, Tailscale, Node, Claude Code, Paperclip, repos, apply.py
paperclip/   the agent team definition (below)
```

```
paperclip/agents/<name>/agent.json   model, role, limits, allowed tools
paperclip/agents/<name>/AGENTS.md    role instructions, with {{CONTEXT}} {{RULES}} {{MISSING_INFO}} placeholders
paperclip/company/context.md         map of the homelab (hosts, endpoints, repos)
paperclip/shared/                    rules and "ask for missing info" shared by all specialists
paperclip/apply.py                   idempotent: hire missing agents, fix drift in config and instructions, list unmanaged agents
```

Team (works only on tickets you assign; no heartbeat/schedules): **Chief of staff** (Haiku, routes and reports), **SRE** (Sonnet: incidents, k3s, observability,
storage and backups; read-only `kubectl`), **Platform** (Sonnet: Terraform/Ansible/Helm/ArgoCD, upgrades and their risk), **Security** (Sonnet: exposure, firewall, TLS, CVEs).

The chief of staff is created by Paperclip onboarding; `apply.py` finds it by role, renames it and syncs it.
To change agents: edit `paperclip/`, merge to `main`, re-run the playbook (it pulls this repo and runs `apply.py`).

## Guardrails

Agents are read-only until their access task is done. That is enforced in layers, not only in the prompts:

- **Allowed tools** per agent in `agent.json` (`--allowedTools`; anything else is denied in headless runs).
- **Claude Code managed settings** (`ansible/files/claude-managed-settings.json` → `/etc/claude-code/managed-settings.json`, root-owned, wins over
  user settings): deny reading Claude/Paperclip credentials, kubeconfig, SSH keys, `.env`, vault and tfstate; deny curl uploads/file output
  (`-d @file`, `-F`, `-T`, `-o`, `file://`) and `git --output`; turn off auto-update and telemetry. The curl patterns are best-effort
  (combined short flags slip through); the egress filter below is the real limit. Plain `curl -X POST` stays allowed because the Paperclip skill uses it for tickets.
- **Egress filter** for the `paperclip` user (nftables, `paperclip-egress.service`): direct traffic only to loopback, DNS and `paperclip_egress_cidrs`
  (the homelab LAN). Everything else goes through tinyproxy on `127.0.0.1:8888`, which only allows `paperclip_egress_domains` and their subdomains.
  A prompt injection in a log line or advisory page cannot send anything to a host you did not list. Blocked attempts are logged as
  `paperclip-egress drop:` (journal) and as `Filtered` in tinyproxy's log. Add domains in `ansible/group_vars/all/vars.yml`; set `paperclip_egress_filter: false` to turn it off.
- **No credentials to write**: repos are HTTPS clones without push access; the kubeconfig is bound to the `view` ClusterRole (no Secrets).
- **Tailscale ACL**: generate the auth key with a tag (`tag:paperclip`) and restrict that tag in the tailnet policy, e.g. allow members to reach
  `tag:paperclip:3100,22` and give `tag:paperclip` no outbound grants.

## Versions

Everything is pinned in `ansible/group_vars/all/vars.yml`: `paperclip_version`, `claude_code_version`, `kubectl_version` (keep it within one minor of k3s).
The service runs the installed `paperclipai` binary, so a restart never pulls a new version. To upgrade: bump the variable, run
`paperclip/apply.py --check` after the playbook to confirm the API still matches, read the Paperclip release notes first.

## Terraform (dedicated Proxmox VM)

`terraform/` provisions the VM that runs Paperclip, modeled on [homelab-infra](https://github.com/luisbrancher/homelab-infra)
(same `bpg/proxmox` provider, same variables, clone of the Debian 13 cloud-init template `9000`, SSH key via cloud-init).

- VM `paperclip`, id 110 (k3s-node is 100, lxc-monitoring is 120), 4 cores, 8GB RAM, 60GB on `local-lvm`; all overridable in `variables.tf`.
- IP is DHCP by default; set `paperclip_ipv4` + `paperclip_gateway` for a static one.
- State lives in HCP Terraform (org `lfck`, workspace `homelab-paperclip-agents`), with the same sensitive variables as homelab-infra:
  `pm_api_url`, `pm_api_token_id`, `pm_api_token_secret`, `ssh_public_key`.

## Ansible (configure the VM)

`ansible/playbooks/paperclip.yml` runs in this order: base packages and user, egress filter (tinyproxy + nftables), Tailscale, Node 24 (NodeSource),
Claude Code + managed settings, Paperclip (`onboard --bind tailnet` + systemd service on :3100), allowed hostnames, this repo and the homelab repos
(+ a 15 min timer that fast-forwards them, since agents cannot `git fetch`), kubectl, `apply.py`, Node Exporter (with the systemd collector).

Tailscale comes up before Paperclip, so `--bind tailnet` works on the first run: the UI and API listen only on the VM's tailnet address,
never on the LAN. `--bind` is only read by the first onboarding; see "Switching an existing install to tailnet" below.

### Vault

`ansible/group_vars/all/vault.yml` (Ansible Vault) holds:

```
tailscale_auth_key: "tskey-auth-..."        # reusable, tagged tag:paperclip
paperclip_board_api_key: "..."              # board API key, used by apply.py (step 8)
```

Edit with `cd ansible && ansible-vault edit group_vars/all/vault.yml`.

## Step by step

1. **HCP Terraform**: create the CLI-driven workspace `homelab-paperclip-agents` in org `lfck` and attach the variable set
   `proxmox-homelab` (`pm_api_url`, `pm_api_token_id`, `pm_api_token_secret` sensitive, `ssh_public_key`).
   Use the same execution mode as the homelab-infra workspace.
2. **Proxmox**: make sure the Debian 13 cloud-init template `9000` (with qemu-guest-agent) exists on node `pve` and the API token has permissions.
   Check the token: `curl -k -H "Authorization: PVEAPIToken=<id>=<secret>" https://<proxmox>:8006/api2/json/version`.
3. **VM**: `cd terraform && terraform login && terraform init && terraform apply`, then `terraform output ip_paperclip`.
4. **Fixed IP**: DHCP reservation for the VM's MAC in OPNsense (or set `paperclip_ipv4`/`paperclip_gateway`), then set the IP in `ansible/inventory.ini`.
5. **Tailscale key**: in the Tailscale admin create a reusable auth key tagged `tag:paperclip` (and the ACL above), put it in the vault as `tailscale_auth_key`.
6. **Ansible**: `cd ansible && ansible-galaxy collection install -r requirements.yml && ansible-playbook site.yml --ask-vault-pass`.
   The first run installs everything and stops short of `apply.py`, printing what is missing.
7. **Claude Code login** (once, interactive): `ssh debian@<ip>` then `sudo -iu paperclip claude login` (goes through the proxy; `~/.profile` sets it).
8. **Paperclip company and board key**: open `http://<tailnet-ip>:3100` (`tailscale ip -4` on the VM), finish onboarding and create the company
   named in `paperclip_company`. Then create a board API key (UI: API keys, or `sudo -iu paperclip paperclipai connect --persona board`,
   which prints `export PAPERCLIP_API_KEY=...`) and store it in the vault as `paperclip_board_api_key`.
   To use the MagicDNS name instead of the IP, add it to `paperclip_allowed_hostnames`.
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
10. **Hire the agents**: re-run `ansible-playbook site.yml --ask-vault-pass`; `apply.py` now runs and its output is printed.
11. **Backups**: add VM 110 to the Proxmox backup job (Datacenter, Backup) next to k3s-node and lxc-monitoring. Paperclip already writes
    its own database dumps to `~/.paperclip/instances/default/data/backups` on the VM; the Proxmox backup takes them off the host.
12. **Monitoring** (in homelab-infra): add `10.10.10.16:9100` to the Prometheus node targets and an alert like
    ```yaml
    - alert: PaperclipDown
      expr: node_systemd_unit_state{instance=~"10.10.10.16:.*",name=~"paperclip.service|paperclip-egress.service|tinyproxy.service",state="active"} == 0
      for: 5m
      labels: {severity: warning}
      annotations: {summary: "{{ $labels.name }} is not active on the paperclip VM"}
    ```

### Switching an existing install to tailnet

An install onboarded with `--bind lan` keeps listening on the LAN. To move it: back it up (`sudo -iu paperclip paperclipai db:backup`),
`sudo systemctl stop paperclip`, `sudo -iu paperclip mv ~/.paperclip ~/.paperclip.lan`, re-run the playbook, and redo step 8
(the company and agents are recreated; `apply.py` hires the specialists again).
