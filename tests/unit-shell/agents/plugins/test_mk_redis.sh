#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# shellcheck source=agents/plugins/mk_redis
MK_SOURCE_ONLY=true source "${UNIT_SH_PLUGINS_DIR}/mk_redis"

oneTimeSetUp() {
    cat <<EOF >"${SHUNIT_TMPDIR}/mk_redis.cfg"

REDIS_INSTANCES=(LOCAL IPHOST test-123)
REDIS_HOST_LOCAL="/var/redis/redis.sock"
REDIS_PORT_LOCAL="unix-socket"

REDIS_HOST_IPHOST="127.0.0.1"
REDIS_PORT_IPHOST="6380"
REDIS_PASSWORD_IPHOST='MYPASSWORD'

REDIS_HOST_test_123="127.0.0.1"
REDIS_PORT_test_123="6379"

REDIS_HOST_cache___="127.0.0.1"
REDIS_PORT_cache___="6381"

EOF
}

test_mk_redis_config() {
    MK_CONFDIR="${SHUNIT_TMPDIR}" load_config
    assertEquals "/var/redis/redis.sock" "$REDIS_HOST_LOCAL"
    assertEquals "unix-socket" "$REDIS_PORT_LOCAL"

    redis_args "LOCAL"
    assertEquals "-s /var/redis/redis.sock info" "${REDIS_ARGS[*]}"

    redis_args "IPHOST"
    assertEquals "-h 127.0.0.1 -p 6380 info" "${REDIS_ARGS[*]}"

    assertEquals "-h" "${REDIS_ARGS[0]}"

}

# An instance name may contain hyphens, a shell variable name may not.
test_mk_redis_config_hyphenated_instance() {
    MK_CONFDIR="${SHUNIT_TMPDIR}" load_config

    redis_args "test-123"
    assertEquals "-h 127.0.0.1 -p 6379 info" "${REDIS_ARGS[*]}"
}

# a rule saved before the Setup field was validated may hold a non-ASCII name
test_mk_redis_config_non_ascii_instance() {
    MK_CONFDIR="${SHUNIT_TMPDIR}" load_config

    redis_args "cache-é"
    assertEquals "-h 127.0.0.1 -p 6381 info" "${REDIS_ARGS[*]}"
}

# shellcheck disable=SC1090 # Can't follow
. "$UNIT_SH_SHUNIT2"
