#!/bin/bash
#
set -e

REPO_PATH="$(dirname "$(dirname "$(realpath "$0")")")"

# acquire sudo to run to change the configuration
sudo true

configure_cognito() {
    idp_url="$1"
    checkmk_port="$2"

    client_id="notused"
    base_url="http://localhost:$checkmk_port"
    well_known="$idp_url/.well-known/openid-configuration"

    # Create JSON object
    JSON=$(printf '{\n "%s":"%s",\n "%s":"%s",\n "%s":"%s",\n "%s":"%s",\n "%s":"%s"\n}' \
        "client_id" "$client_id" \
        "base_url" "$base_url" \
        "saas_api_url" "$idp_url" \
        "tenant_id" "123tenant567" \
        "well_known" "$well_known")

    # Write JSON object to file
    sudo mkdir -p /etc/cse
    echo "$JSON" | sudo tee /etc/cse/cognito-cmk.json >/dev/null
}

PORT=5551
# URL under which we can reach the openid provider
export URL="http://localhost:${PORT}"

# checkmk uses port 5000 by default
configure_cognito $URL 5000

export PYTHONPATH="${REPO_PATH}/tests/testlib"
"$REPO_PATH"/scripts/run-pipenv run uvicorn openid_oauth_provider:application --port "$PORT"
