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
    azure = {
      version = ">= 1.3.1"
      source  = "github.com/hashicorp/azure"
    }
    amazon = {
      version = ">= 1.1.1"
      source  = "github.com/hashicorp/amazon"
    }
  }
}


source "qemu" "builder" {
  vm_name          = "ubuntu-2204-amd64-qemu-build"
  iso_url          = "http://www.releases.ubuntu.com/22.04/ubuntu-22.04.1-live-server-amd64.iso"
  iso_checksum     = "sha256:10f19c5b2b8d6db711582e0e27f5116296c34fe4b313ba45f9b201a5007056cb"
  memory           = 1024
  disk_image       = false
  output_directory = var.qemu_output_dir_name
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
  client_id                           = "${var.azure_client_id}"
  client_secret                       = "${var.azure_client_secret}"
  image_offer                         = "0001-com-ubuntu-server-jammy"
  image_publisher                     = "Canonical"
  image_sku                           = "22_04-lts"
  build_resource_group_name           = var.azure_build_resource_group_name
  virtual_network_resource_group_name = var.azure_virtual_network_resource_group_name
  virtual_network_name                = var.azure_virtual_network_name
  virtual_network_subnet_name         = var.azure_virtual_network_subnet_name
  managed_image_name                  = var.azure_image_name
  managed_image_resource_group_name   = "${var.azure_resource_group}"
  os_type                             = "Linux"
  subscription_id                     = "${var.azure_subscription_id}"
  tenant_id                           = "${var.azure_tenant_id}"
  vm_size                             = "Standard_DS2_v2"
}

# https://cloud-images.ubuntu.com/locator/ec2/
# filter for region=us-east-1, arch=amd64, version=latest lts
source "amazon-ebs" "builder" {
  region        = "us-east-1"
  access_key    = var.aws_access_key
  secret_key    = var.aws_secret_key
  source_ami    = "ami-04ab94c703fb30101"
  instance_type = "t2.micro"
  ssh_username  = "ubuntu"
  ami_name      = var.aws_ami_name
}


build {
  name = "checkmk-ansible"
  sources = [
    "source.qemu.builder",
    "source.amazon-ebs.builder",
    "source.azure-arm.builder"
  ]
  # wait a minute for backround update processes. Might help with flakyness
  provisioner "shell" {
    inline = [
      "sleep 60",
    ]
  }
  # setup apt-get
  provisioner "shell" {
    inline = [
      "echo 'debconf debconf/frontend select Noninteractive' | sudo debconf-set-selections",
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
    role_paths    = ["./roles/change-motd/", "./roles/configure-apache/", "./roles/checkmk/"]
    extra_arguments = [
      "--extra-vars",
      "checkmk_server_version=${var.cmk_version}",
      "--extra-vars",
      "checkmk_server_download_user=${var.cmk_download_user}",
      "--extra-vars",
    "checkmk_server_download_pass=${var.cmk_download_pass}", ]
  }
  # update user
  provisioner "ansible-local" {
    playbook_file = "./qemu-playbook.yml"
    only          = ["qemu.builder"]
  }
  provisioner "ansible-local" {
    playbook_file = "./azure-playbook.yml"
    only          = ["azure-arm.builder"]
  }
  provisioner "ansible-local" {
    playbook_file = "./aws-playbook.yml"
    only          = ["amazon-ebs.builder"]
  }
  # uninstall ansible
  provisioner "shell" {
    inline = [
      "sudo add-apt-repository --yes --remove ppa:ansible/ansible",
      "sudo apt-get remove -y -q software-properties-common ansible",
      "sudo apt autoremove -y -q"
    ]
  }
}
