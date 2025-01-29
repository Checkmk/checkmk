#!/usr/bin/env bash
# Launch a cognito idp for the SaaS edition
set -e

REPO_PATH="$(dirname "$(dirname "$(realpath "$0")")")"

# acquire sudo to run to change the configuration
sudo true

# PORT and URL under which we can reach the openid provider
if [[ "$1" == *"://"* ]]; then
    export URL=$1
    HOST=$(echo "${URL}" | cut -d: -f2 | sed "s-^//--")
    PORT=$(echo "${URL}" | cut -d: -f3)
else
    HOST=localhost
    PORT=${1:-5551}
    export URL=http://${HOST}:${PORT}
fi

# URL of the checkmk instance; checkmk uses port 5000 by default
CMK_URL=${2:-http://localhost:5000}

# Write cognito configuration file
sudo mkdir -p /etc/cse
"$(dirname "$0")/create_cognito_config_cse.sh" "${URL}" "${CMK_URL}" "notused" "092fd467-0d2f-4e0a-90b8-4ee6494f7453" | sudo tee /etc/cse/cognito-cmk.json >/dev/null

CSE_UAP_URL=https://admin-panel.saas-prod.cloudsandbox.checkmk.cloud/
json_string=$(jq --null-input \
    --arg uap_url "$CSE_UAP_URL" \
    --arg bug_tracker_url "${CSE_UAP_URL}bug-report" \
    '{"uap_url": $uap_url, "bug_tracker_url": $bug_tracker_url, "download_agent_user": "automation", "tenant_id": "092fd467-0d2f-4e0a-90b8-4ee6494f7453"}')

echo "$json_string" | jq "." | sudo tee /etc/cse/admin_panel_url.json >/dev/null

CSE_LICENSE_SECRET_PATH=/etc/cse/client-secret
json_string=$(jq --null-input \
    --arg secret_path "$CSE_LICENSE_SECRET_PATH" \
    '{"secret_path": $secret_path}')

echo "$json_string" | jq "." | sudo tee /etc/cse/cmk_license_settings.json >/dev/null

# Write the test license secret to a file
CSE_LICENSE_SECRET=$(head -c 32 /dev/urandom | sha256sum -z | awk -F' ' '{{printf($1)}}')
echo "$CSE_LICENSE_SECRET" | sudo tee "$CSE_LICENSE_SECRET_PATH" >/dev/null

export PYTHONPATH="${REPO_PATH}"
"${REPO_PATH}/scripts/run-uvenv" uvicorn tests.testlib.cse.openid_oauth_provider:application --host "${HOST}" --port "${PORT}"
