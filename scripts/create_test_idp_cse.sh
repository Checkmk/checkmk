#!/usr/bin/env bash
# Launch a cognito idp for the SaaS edition
set -e

REPO_PATH="$(dirname "$(dirname "$(realpath "$0")")")"

# acquire sudo to run to change the configuration
sudo true

# PORT and URL under which we can reach the openid provider
PORT=${1:-5551}
export URL="http://localhost:${PORT}"

# URL of the checkmk instance; checkmk uses port 5000 by default
CMK_URL="http://localhost:${2:-5000}"

# Write cognito configuration file
sudo mkdir -p /etc/cse
"$(dirname "$0")/create_cognito_config_cse.sh" "${URL}" "${CMK_URL}" | sudo tee /etc/cse/cognito-cmk.json >/dev/null

export PYTHONPATH="${REPO_PATH}:${REPO_PATH}/tests/testlib"
"${REPO_PATH}/scripts/run-pipenv" run uvicorn cse.openid_oauth_provider:application --port "${PORT}"
