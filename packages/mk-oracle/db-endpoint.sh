#!/bin/bash
# Shared endpoint resolution for the mk-oracle component-test runners.
# Source this file (from the package directory) and call
# resolve_test_endpoint; it exports CI_ORA2_DB_TEST in the format
#   host:user:password:port:instance:role:service_name:sid:custom3
# from CMK-23904, which reserves the trailing custom3 slot; "_" marks
# an unset field.
#
# A pre-set CI_ORA2_DB_TEST is used verbatim; otherwise the CI endpoint
# is constructed from CI_ORA_TEST_PASSWORD. Endpoint constants live in
# test-db-endpoints.conf.

# shellcheck source=test-db-endpoints.conf
. "$(dirname "${BASH_SOURCE[0]}")/test-db-endpoints.conf"

_endpoint_failure() {
    if declare -F failure >/dev/null; then
        failure "$@"
    else
        echo "$(basename "$0"):" "$@" >&2
        exit 1
    fi
}

resolve_test_endpoint() {
    if [[ -z "${CI_ORA2_DB_TEST:-}" ]]; then
        [[ -n "${CI_ORA_TEST_PASSWORD:-}" ]] ||
            _endpoint_failure "no test database configured; either export CI_ORA2_DB_TEST" \
                "(full endpoint) or CI_ORA_TEST_PASSWORD (CI database), or run the local" \
                "Docker database via ./run --docker-tests"
        export CI_ORA2_DB_TEST="$ci_host:$ci_user:$CI_ORA_TEST_PASSWORD:$ci_port:$ci_instance::$ci_service:$ci_sid:_:"
    fi
    # stderr: run_legacy.sh/run_unified.sh compare their stdout as agent output
    echo "component tests use the database at ${CI_ORA2_DB_TEST%%:*}" >&2
}

# Explode the resolved endpoint into the DB_* variables the legacy
# comparison scripts substitute into their config templates. Values
# already present in the environment win; "_" (unset field, mapped to
# None by SqlDbEndpoint::from_str) becomes empty.
export_db_vars_from_endpoint() {
    local host user password port instance role service sid
    IFS=':' read -r host user password port instance role service sid _ \
        <<<"${CI_ORA2_DB_TEST}"
    : "$instance" "$role" # unused fields
    [[ "${service}" == "_" ]] && service=
    [[ "${sid}" == "_" ]] && sid=
    export DB_HOST="${DB_HOST:-${host}}"
    export DB_USER="${DB_USER:-${user}}"
    export DB_PASSWORD="${DB_PASSWORD:-${password}}"
    export DB_PORT="${DB_PORT:-${port}}"
    export DB_SERVICE_NAME="${DB_SERVICE_NAME:-${service}}"
    export DB_SID="${DB_SID:-${sid}}"
}
