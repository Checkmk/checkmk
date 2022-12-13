packer {
  required_plugins {
    qemu = {
      version = ">= 0.0.7"
      source  = "github.com/hashicorp/qemu"
    }
    ansible = {
      version = ">= 1.0.3"
      source  = "github.com/hashicorp/ansible"
    }
  }
}


source "qemu" "ubuntu-2204-amd64-qemu" {
  vm_name          = "ubuntu-2204-amd64-qemu-build"
  iso_url          = "http://www.releases.ubuntu.com/22.04/ubuntu-22.04.1-live-server-amd64.iso"
  iso_checksum     = "sha256:10f19c5b2b8d6db711582e0e27f5116296c34fe4b313ba45f9b201a5007056cb"
  memory           = 1024
  disk_image       = false
  output_directory = "output-ubuntu-2204-amd64-qemu"
  accelerator      = "kvm"
  disk_size        = "15000M"
  disk_interface   = "virtio"
  format           = "qcow2"
  net_device       = "virtio-net"
  boot_wait        = "3s"
  boot_command = [
    "<esc><esc><esc><esc>e<wait>",
        "<del><del><del><del><del><del><del><del>",
        "<del><del><del><del><del><del><del><del>",
        "<del><del><del><del><del><del><del><del>",
        "<del><del><del><del><del><del><del><del>",
        "<del><del><del><del><del><del><del><del>",
        "<del><del><del><del><del><del><del><del>",
        "<del><del><del><del><del><del><del><del>",
        "<del><del><del><del><del><del><del><del>",
        "<del><del><del><del><del><del><del><del>",
        "<del><del><del><del><del><del><del><del>",
        "<del><del><del><del><del><del><del><del>",
        "<del><del><del><del><del><del><del><del>",
        "<del><del><del><del><del><del><del><del>",
        "<del><del><del><del><del><del><del><del>",
        "<del><del><del><del><del><del><del><del>",
        "linux /casper/vmlinuz --- autoinstall ds=\"nocloud-net;seedfrom=http://{{.HTTPIP}}:{{.HTTPPort}}/\"<enter><wait>",
        "initrd /casper/initrd<enter><wait>",
        "boot<enter>",
        "<enter><f10><wait>"
  ]
  http_directory   = "http-server"
  shutdown_command = "echo 'packer' | sudo -S shutdown -P now"
  ssh_username     = "ubuntu"
  ssh_password     = "ubuntu"
  ssh_timeout      = "60m"
}

source "azure-arm" "builder" {
  azure_tags = {
    dept = "Engineering"
    task = "Image deployment"
  }
  client_id                         = "${var.azure_client_id}"
  client_secret                     = "${var.azure_client_secret}"
  image_offer                       = "0001-com-ubuntu-server-jammy"
  image_publisher                   = "Canonical"
  image_sku                         = "22_04-lts"
  location                          = "East US"
  managed_image_name                = "cmk"
  managed_image_resource_group_name = "myResourceGroup"
  os_type                           = "Linux"
  subscription_id                   = "${var.azure_subscription_id}"
  tenant_id                         = "${var.azure_tenant_id}"
  vm_size                           = "Standard_DS2_v2"
}

build {
  name = "checkmk-ansible"
  sources = [
    # "source.qemu.ubuntu-2204-amd64-qemu"
    "source.azure-arm.builder"
  ]
  # setup apt-get
  provisioner "shell" {
    inline = [
       "echo 'debconf debconf/frontend select Noninteractive' | sudo debconf-set-selections",
       "sudo apt-get update",
    ]
  }
  # install ansible
  provisioner "shell" {
    inline = [
       "sudo apt-get install -y -q software-properties-common",
       "sudo add-apt-repository --yes --update ppa:ansible/ansible",
       "sudo apt-get update",
       "sudo apt-get install -y -q ansible",
    ]
  }
  # run playbook
  provisioner "ansible-local" {
    playbook_file = "./playbook.yml"
    galaxy_file = "./requirements.yml"
    galaxy_collections_path = "/tmp/ansible/collections"
  }
  # update user
  provisioner "shell" {
    inline = [
       "sudo passwd --expire $(whoami)",
    ]
  }
}
