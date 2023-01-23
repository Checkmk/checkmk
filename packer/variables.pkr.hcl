// Azure variables
variable "azure_client_id" {
  type      = string
  sensitive = true
}
variable "azure_client_secret" {
  type      = string
  sensitive = true
}
variable "azure_subscription_id" {
  type      = string
  sensitive = true
}
variable "azure_tenant_id" {
  type      = string
  sensitive = true
}
variable "azure_resource_group" {
  type = string
}
variable "azure_build_resource_group_name" {
  type = string
}
variable "azure_virtual_network_resource_group_name" {
  type = string
}
variable "azure_virtual_network_name" {
  type = string
}
variable "azure_virtual_network_subnet_name" {
  type = string
}
variable "azure_image_name" {
  type = string
}

// AWS
variable "aws_access_key" {
  type      = string
  sensitive = true
}
variable "aws_secret_key" {
  type      = string
  sensitive = true
}
variable "aws_ami_name" {
  type = string
}

// Qemu
variable "qemu_output_dir_name" {
  type = string
}

// Ansible variables
variable "cmk_version" {
  # set the cmk version to build.
  type = string
}
variable "cmk_download_user" {
  type      = string
  sensitive = true
}
variable "cmk_download_pass" {
  type      = string
  sensitive = true
}
