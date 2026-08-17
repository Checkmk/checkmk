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
  vm_name          = "ubuntu-2404-amd64-qemu-build"
  iso_url          = "https://www.releases.ubuntu.com/24.04/ubuntu-24.04.4-live-server-amd64.iso"
  iso_checksum     = "sha256:e907d92eeec9df64163a7e454cbc8d7755e8ddc7ed42f99dbc80c40f1a138433"
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
  image_offer                         = "ubuntu-24_04-lts"
  image_publisher                     = "Canonical"
  # Gen1 (V1) SKU: must match the hypervisor generation of the existing
  # image definitions in the marketplace / compute gallery
  image_sku                           = "server-gen1"
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
  region     = "us-east-1"
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
  # pinned to one specific release serial for reproducible builds; find newer
  # serials at https://cloud-images.ubuntu.com/releases/streams/v1/com.ubuntu.cloud:released:aws.json
  # (currently resolves to ami-052355af2a014bd2c in us-east-1)
  source_ami_filter {
    filters = {
      name                = "ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-20260714"
      root-device-type    = "ebs"
      virtualization-type = "hvm"
    }
    # Canonical
    owners = ["099720109477"]
  }
  instance_type = "t2.micro"
  ssh_username  = "ubuntu"
  ami_name      = var.aws_ami_name
  # the 8GB root volume of the base AMI is too small for the checkmk
  # package + site + dist-upgrade; this also becomes the AMI's volume size
  launch_block_device_mappings {
    device_name           = "/dev/sda1"
    volume_size           = 15
    volume_type           = "gp3"
    delete_on_termination = true
  }
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
