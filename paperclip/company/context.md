## Homelab (source of truth: the repos in your working directory (AGENTS_CWD, ~/homelab on the paperclip VM); if they disagree with this map, report the drift)
- N150: OPNsense bare metal (router, firewall, VLANs trusted 10, iot 20, guest 30, lab 40).
- Proxmox (m80q, API https://10.10.10.10:8006): VM k3s-node (8 cores, 16GB RAM, 50GB OS disk + 220GB media-ssd; k3s, ArgoCD, Nextcloud, Immich, Jellyfin, cert-manager, CNPG), LXC lxc-monitoring (Prometheus, Grafana, Loki) and VM paperclip (this team).
- NAS: TrueNAS on a dedicated Lenovo V50s (i3-10100), ZFS, NFS shares. Not a Proxmox VM. Not scraped by Prometheus yet.
- Pi4: Omada Controller (docker), MotionEye (cameras), UpSnap (Wake-on-LAN). Managed switch and OpenWrt AP. Tailscale on hosts.
- Repos (cwd): homelab-gitops (ArgoCD + Helm), homelab-infra (Terraform + Ansible), homelab-network (Ansible for OPNsense/AP).

## Endpoints (no secrets; credentials live elsewhere, ask where)
- k3s-node 10.10.10.11 (node exporter :9100, k3s API :6443; read-only kubeconfig at ~/.kube/config)
- lxc-monitoring 10.10.10.13: Prometheus :9090, Grafana :3000, Loki :3100
- Pi4 10.10.10.14: Omada :8043, UpSnap :8090, MotionEye :8765, node exporter :9100
- TrueNAS 10.10.10.15
- paperclip 10.10.10.16: Paperclip :3100
Use these before asking the board for endpoints.
