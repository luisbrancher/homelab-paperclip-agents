resource "proxmox_virtual_environment_vm" "paperclip" {
  name        = var.paperclip_server
  description = "Paperclip + agents. Managed by Terraform."
  tags        = ["paperclip", "terraform"]
  node_name   = var.proxmox_node
  vm_id       = var.paperclip_vm_id
  on_boot     = true

  clone {
    vm_id = var.vm_template_id
  }

  agent {
    enabled = true
  }

  cpu {
    cores = var.paperclip_cores
    type  = "host"
  }

  memory {
    dedicated = var.paperclip_memory_mb
  }

  disk {
    interface    = "scsi0"
    size         = var.paperclip_disk_gb
    datastore_id = var.storage_pool
  }

  network_device {
    bridge = var.network_bridge
    model  = "virtio"
  }

  initialization {
    ip_config {
      ipv4 {
        address = var.paperclip_ipv4
        gateway = var.paperclip_ipv4 == "dhcp" ? null : var.paperclip_gateway
      }
    }
    user_account {
      keys = [var.ssh_public_key]
    }
  }
}
