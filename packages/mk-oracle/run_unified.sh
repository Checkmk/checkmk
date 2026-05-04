#!/bin/bash
# Run mk-oracle as it has been built
# config asnd log are located in the tests/regression
# Usage: ./run_unified.sh [--binary <path>]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BINARY=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --binary)
            BINARY="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# agent setup
PKG_DIR="${SCRIPT_DIR}/tests/regression/mk-oracle"
export MK_CONFDIR="${PKG_DIR}/etc/check_mk"
export MK_LOGDIR="${PKG_DIR}/var/log/check_mk_agent"

# config setup
export DB_USER="system"
export DB_PASSWORD="${CI_ORA_TEST_PASSWORD}"
export DB_HOST="oracle-rocky-ci.lan.checkmk.net"
export DB_SERVICE_NAME="dbtest23"
export DB_SECTION="${DB_SECTION:-instance}"
envsubst <"${MK_CONFDIR}/mk-oracle.yml.conf" >"${MK_CONFDIR}/mk-oracle.yml"

# run
if [[ -n "${BINARY}" ]]; then
    path_to_runtime="${SCRIPT_DIR}/runtimes/plugins/packages/mk-oracle"
    export LD_LIBRARY_PATH="${path_to_runtime}:${LD_LIBRARY_PATH}"
    "${BINARY}" -c "${PKG_DIR}/etc/check_mk/mk-oracle.yml"
else
    ./cargo_run run -- -c "${PKG_DIR}/etc/check_mk/mk-oracle.yml"
fi
