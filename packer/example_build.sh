#!/usr/bin/bash

# azure
export PKR_VAR_azure_client_id=""
export PKR_VAR_azure_client_secret=""
export PKR_VAR_azure_subscription_id=""
export PKR_VAR_azure_tenant_id=""
export PKR_VAR_azure_resource_group=""
export PKR_VAR_azure_build_resource_group_name=""
export PKR_VAR_azure_virtual_network_resource_group_name=""
export PKR_VAR_azure_virtual_network_name=""
export PKR_VAR_azure_virtual_network_subnet_name=""

# ansible
export PKR_VAR_cmk_version=""
export PKR_VAR_cmk_download_user=""
export PKR_VAR_cmk_download_pass=""

packer init .
packer build "$@"
