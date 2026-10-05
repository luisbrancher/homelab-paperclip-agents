## Homelab (source of truth: the repos in /home/luisf/homelab; if they disagree with this map, report the drift)
- N150: OPNsense bare metal (router, firewall, VLANs trusted 10, iot 20, guest 30, lab 40).
- Proxmox (m80q): VM k3s-node (8 cores, 16GB RAM, 50GB OS disk + 220GB media-ssd; k3s, ArgoCD, Nextcloud, Immich, Jellyfin, cert-manager, CNPG) and LXC lxc-monitoring (Prometheus, Grafana, Loki).
- NAS: TrueNAS on a dedicated Lenovo V50s (i3-10100), ZFS, NFS shares. Not a Proxmox VM.
- Pi4: Omada Controller (docker), MotionEye (cameras), UpSnap (Wake-on-LAN). Managed switch and OpenWrt AP. Tailscale on hosts.
- Repos (cwd): homelab-gitops (ArgoCD + Helm), homelab-infra (Terraform + Ansible), homelab-network (Ansible for OPNsense/AP).
S