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
// Ansible variables
variable "cmk_version" {
  # set the cmk version to build.
  type      = string
}
variable "cmk_download_user" {
  type      = string
  sensitive = true
}
variable "cmk_download_pass" {
  type      = string
  sensitive = true
}
