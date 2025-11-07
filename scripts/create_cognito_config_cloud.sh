#!/usr/bin/env bash
# Generate and print the cognito idp config for the SaaS edition

IDP_URL="${1-http://localhost:5551}"
BASE_URL="${2:-http://localhost:5000}"
CLIENT_ID="${3:-notused}"
TENANT_ID="${4:-092fd467-0d2f-4e0a-90b8-4ee6494f7453}"

# Create JSON object
printf '{\n "%s":"%s",\n "%s":"%s",\n "%s":"%s",\n "%s":"%s",\n "%s":"%s",\n "%s":"%s"\n}' \
    "client_id" "$CLIENT_ID" \
    "base_url" "$BASE_URL" \
    "saas_api_url" "$IDP_URL" \
    "tenant_id" "$TENANT_ID" \
    "logout_url" "$IDP_URL/logout" \
    "well_known" "$IDP_URL/.well-known/openid-configuration"
