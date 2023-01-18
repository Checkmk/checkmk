#!/usr/bin/bash

# azure
export PKR_VAR_azure_client_id=""
export PKR_VAR_azure_client_secret=""
export PKR_VAR_azure_subscription_id=""
export PKR_VAR_azure_tenant_id=""

# ansible
export PKR_VAR_cmk_version=""
export PKR_VAR_cmk_download_user=""
export PKR_VAR_cmk_download_pass=""

packer init .
packer build "$@"
