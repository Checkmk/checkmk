#!/bin/bash
# Run mk-oracle as it has been built
# config asnd log are located in the tests/regression

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# agent setup
PKG_DIR="${SCRIPT_DIR}/tests/regression/mk-oracle"
export MK_CONFDIR="${PKG_DIR}/etc/check_mk"
export MK_LOGDIR="${PKG_DIR}/var/log/check_mk_agent"

# config setup
export DB_USER="system"
export DB_PASSWORD="${CI_ORA2_DB_TEST_PASSWORD}"
export DB_HOST="ora-rocktest.dev.checkmk.net"
export DB_SERVICE_NAME="FREE.cmkoratest"
export DB_SECTION="${DB_SECTION:-instance}"
envsubst <"${MK_CONFDIR}/oracle.yml.conf" >"${MK_CONFDIR}/oracle.yml"

# run
./cargo_run run -- -c "${PKG_DIR}/etc/check_mk/oracle.yml"
