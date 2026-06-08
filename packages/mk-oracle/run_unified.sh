#!/bin/bash
# Run mk-oracle as it has been built
# config asnd log are located in the tests/regression
# Usage: ./run_unified.sh
# Set RELEASE_BIN env var to use a pre-built binary instead of cargo run.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# agent setup
PKG_DIR="${SCRIPT_DIR}/tests/regression/mk-oracle"
export MK_CONFDIR="${PKG_DIR}/etc/check_mk"
export MK_LOGDIR="${PKG_DIR}/var/log/check_mk_agent"

# config setup
export DB_USER="system"
export DB_PASSWORD="${CI_ORA_TEST_PASSWORD}"
export DB_HOST="${DB_HOST:-oracle-rocky-ci.lan.checkmk.net}"
export DB_PORT="${DB_PORT:-1521}"
export DB_SERVICE_NAME="${DB_SERVICE_NAME:-dbtest23}"
export DB_SECTION="${DB_SECTION:-instance}"
if [[ "${DB_SECTION}" == "all" ]]; then
    export INDIVIDUAL_SECTIONS="_unused"
    export ALL_SECTIONS="sections"
else
    export INDIVIDUAL_SECTIONS="sections"
    export ALL_SECTIONS="_unused"
fi
envsubst <"${MK_CONFDIR}/mk-oracle.yml.conf" >"${MK_CONFDIR}/mk-oracle.yml"

# run
if [[ -n "${RELEASE_BIN}" ]]; then
    path_to_runtime="${SCRIPT_DIR}/runtimes/plugins/packages/mk-oracle"
    export LD_LIBRARY_PATH="${path_to_runtime}:${LD_LIBRARY_PATH}"
    export TNS_ADMIN="${SCRIPT_DIR}/tests/files/tns"
    export MK_LIBDIR="${SCRIPT_DIR}/runtimes/"
    "${RELEASE_BIN}" -c "${PKG_DIR}/etc/check_mk/mk-oracle.yml"
else
    ./cargo_run run -- -c "${PKG_DIR}/etc/check_mk/mk-oracle.yml"
fi
