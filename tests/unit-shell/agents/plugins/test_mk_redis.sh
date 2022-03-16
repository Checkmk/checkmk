#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# shellcheck source=agents/plugins/mk_redis
MK_SOURCE_ONLY=true source "${UNIT_SH_PLUGINS_DIR}/mk_redis"

oneTimeSetUp() {
    cat <<EOF >"${SHUNIT_TMPDIR}/mk_redis.cfg"

REDIS_INSTANCES=(LOCAL IPHOST)
REDIS_HOST_LOCAL="/var/redis/redis.sock"
REDIS_PORT_LOCAL="unix-socket"

REDIS_HOST_IPHOST="127.0.0.1"
REDIS_PORT_IPHOST="6380"
REDIS_PASSWORD_IPHOST='MYPASSWORD'

EOF
}

test_mk_redis_config() {
    MK_CONFDIR="${SHUNIT_TMPDIR}" load_config
    assertEquals "/var/redis/redis.sock" "$REDIS_HOST_LOCAL"
    assertEquals "unix-socket" "$REDIS_PORT_LOCAL"

    redis_args "LOCAL"
    assertEquals "-s /var/redis/redis.sock info" "${REDIS_ARGS[*]}"

    redis_args "IPHOST"
    assertEquals "-h 127.0.0.1 -p 6380 -a MYPASSWORD info" "${REDIS_ARGS[*]}"

    assertEquals "-h" "${REDIS_ARGS[0]}"
    assertEquals "MYPASSWORD" "${REDIS_ARGS[5]}"

}

# shellcheck disable=SC1090 # Can't follow
. "$UNIT_SH_SHUNIT2"
