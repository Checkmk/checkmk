#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

MK_REDIS_PLUGIN_PATH="$UNIT_SH_PLUGINS_DIR/mk_redis"

oneTimeSetUp() {
    MK_CONFDIR=${SHUNIT_TMPDIR}
    REDIS_CLI_CMD=echo
    WAITMAX_CMD=echo
    cat <<EOF >"${MK_CONFDIR}/mk_redis.cfg"

REDIS_INSTANCES=(LOCAL IPHOST)
REDIS_HOST_LOCAL="/var/redis/redis.sock"
REDIS_PORT_LOCAL="unix-socket"

REDIS_HOST_IPHOST="127.0.0.1"
REDIS_PORT_IPHOST="6380"
REDIS_PASSWORD_IPHOST='MYPASSWORD'

EOF
    . "$MK_REDIS_PLUGIN_PATH" >/dev/null
}

test_load_config() {
    load_config
    assertEquals "/var/redis/redis.sock" "$REDIS_HOST_LOCAL"
    assertEquals "unix-socket" "$REDIS_PORT_LOCAL"
}

test_redis_args() {
    redis_args LOCAL
    assertEquals "-s $REDIS_HOST_LOCAL info" "${REDIS_ARGS[*]}"
    redis_args IPHOST
    assertEquals "-h $REDIS_HOST_IPHOST -p $REDIS_PORT_IPHOST -a $REDIS_PASSWORD_IPHOST info" "${REDIS_ARGS[*]}"

    assertEquals "-h" "${REDIS_ARGS[0]}"
    assertEquals "$REDIS_PASSWORD_IPHOST" "${REDIS_ARGS[5]}"

}

. "$UNIT_SH_SHUNIT2"
