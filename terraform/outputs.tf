output "ip_paperclip" {
  description = "IP from the paperclip VM"
  value       = try(proxmox_virtual_environment_vm.paperclip.ipv4_addresses[1][0], "dhcp - check proxmox UI")
}
