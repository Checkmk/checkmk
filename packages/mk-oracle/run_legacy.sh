#!/bin/bash
# Run mk_oracle (old bash-based plugin) from the extracted check-mk-agent package directory.
# Replicates the environment that check_mk_agent + systemd would set up.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_DIR="${SCRIPT_DIR}/tests/regression/mk_oracle"

# Environment variables exported by check_mk_agent
export MK_LIBDIR="${PKG_DIR}/usr/lib/check_mk_agent"
export MK_CONFDIR="${PKG_DIR}/etc/check_mk"
export MK_VARDIR="${PKG_DIR}/var/lib/check_mk_agent"
export MK_LOGDIR="${PKG_DIR}/var/lib/check_mk_agent/log"
export LC_ALL=C.UTF-8

mkdir -p "$MK_LOGDIR" >/dev/null 2>&1
mkdir -p "$MK_VARDIR" >/dev/null 2>&1

# TNS_ADMIN defaults to MK_CONFDIR in the script (for sqlnet.ora)
export TNS_ADMIN="${MK_CONFDIR}"

# DB_* from the resolved endpoint (CI_ORA2_DB_TEST verbatim if set, else
# the CI database from CI_ORA_TEST_PASSWORD, see db-endpoint.sh);
# pre-set DB_* values win.
. "${SCRIPT_DIR}/db-endpoint.sh"
resolve_test_endpoint
export_db_vars_from_endpoint
export DB_SECTION="${DB_SECTION:-instance}"
if [[ "${DB_SECTION}" == "all" ]]; then
    export INDIVIDUAL_SECTIONS="#SYNC_SECTIONS"
    export ALL_SECTIONS="SYNC_SECTIONS"
else
    export INDIVIDUAL_SECTIONS="SYNC_SECTIONS"
    export ALL_SECTIONS="#SYNC_SECTIONS"
fi
envsubst <"${MK_CONFDIR}/mk_oracle.cfg.conf" >"${MK_CONFDIR}/mk_oracle.cfg"

# sqlplus
export ORACLE_HOME="${ORACLE_HOME:-/opt/ora}"
export LD_LIBRARY_PATH="${ORACLE_HOME}/bin:$LD_LIBRARY_PATH"

if [ ! -x "${ORACLE_HOME}/bin/sqlplus" ]; then
    echo "ERROR: sqlplus not found or not executable: ${ORACLE_HOME}/bin/sqlplus" >&2
    exit 1
fi

exec "${SCRIPT_DIR}/../../agents/plugins/mk_oracle" --no-spool "$@"
