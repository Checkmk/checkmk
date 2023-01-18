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
variable "build_resource_group_name" {
  type = string
}
variable "virtual_network_resource_group_name" {
  type = string
}
variable "virtual_network_name" {
  type = string
}
variable "virtual_network_subnet_name" {
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
