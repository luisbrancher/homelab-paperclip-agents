# auth variables (same as homelab-infra; set as sensitive variables in HCP Terraform)
variable "pm_api_url" {
  description = "URL da API do Proxmox"
  type        = string
}

variable "pm_api_token_id" {
  description = "Token ID do Proxmox (ex: terraform@pve!terraform-token)"
  type        = string
}

variable "pm_api_token_secret" {
  description = "Token secret do Proxmox"
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "ED25519 public key for SSH access"
  type        = string
}

# VM
variable "paperclip_server" {
  description = "Name of the Paperclip VM"
  type        = string
  default     = "paperclip"
}

variable "paperclip_vm_id" {
  description = "Proxmox VM ID (homelab-infra uses 100 for k3s-node and 120 for lxc-monitoring)"
  type        = number
  default     = 110
}

variable "paperclip_cores" {
  type    = number
  default = 4
}

variable "paperclip_memory_mb" {
  type    = number
  default = 8192
}

variable "paperclip_disk_gb" {
  type    = number
  default = 60
}

variable "paperclip_ipv4" {
  description = "Static IPv4 in CIDR (e.g. 10.10.10.16/24) or \"dhcp\""
  type        = string
  default     = "dhcp"
}

variable "paperclip_gateway" {
  description = "Gateway, only used when paperclip_ipv4 is static"
  type        = string
  default     = null
}

# infra variables (same defaults as homelab-infra)
variable "proxmox_node" {
  type    = string
  default = "pve"
}

variable "network_bridge" {
  type    = string
  default = "vmbr0"
}

variable "vm_template_id" {
  description = "VM ID do template base (Debian 13 + cloud-init + qemu-guest-agent)"
  type        = number
  default     = 9000
}

variable "storage_pool" {
  type    = string
  default = "local-lvm"
}
