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
export PKR_VAR_azure_image_name="checkmk"

# aws
export PKR_VAR_aws_secret_key=""
export PKR_VAR_aws_access_key=""
export PKR_VAR_aws_ami_name="checkmk"

# qemu
export PKR_VAR_qemu_output_dir_name="checkmk"

# ansible
export PKR_VAR_cmk_version=""
export PKR_VAR_cmk_download_user=""
export PKR_VAR_cmk_download_pass=""

packer init .
packer build "$@"
