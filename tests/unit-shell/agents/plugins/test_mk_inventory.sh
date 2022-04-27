#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# shellcheck source=agents/plugins/mk_inventory.linux
MK_SOURCE_AGENT="yes" . "${UNIT_SH_AGENTS_DIR}/plugins/mk_inventory.linux"

_is_timestamp() {
    echo "${*}" | grep -qE '^[1-9][0-9]{9}$' # update this in 2286
}

test__get_epoch_with_date() {
    # make sure our `date` is ok
    assertTrue "_is_timestamp \"$(date +%s)\""
    TS="$(_get_epoch)"
    assertTrue "_is_timestamp ${TS}"
}

test__get_epoch_with_failing_date() {
    # this will fail if the testing system does not provide perl; which is ok
    command -v perl || return

    date() { false; }
    TS="$(_get_epoch)"
    unset date
    assertTrue "_is_timestamp ${TS}"
}

test__get_epoch_with_dim_date() {
    # this will fail if the testing system does not provide perl; which is ok
    command -v perl || return

    date() { echo "%s"; }
    TS="$(_get_epoch)"
    unset date
    assertTrue "_is_timestamp ${TS}"
}

test_persist_intertion() {

    _sections() {
        echo "<<<this_needs_the_option:sep(52)>>>"
        echo "this is just: a line"
        echo "<<<this_already_has_the_option:persist(123)>>>"
    }

    assertEquals \
        $'<<<this_needs_the_option:sep(52):persist(456)>>>\nthis is just: a line\n<<<this_already_has_the_option:persist(123)>>>' \
        "$(_sections | _insert_persist_option "456")"
}

oneTimeSetUp() {
    export MK_VARDIR="${SHUNIT_TMPDIR}"

    INVENTORY_CONFIG="$MK_VARDIR/test_mk_inventory.cfg"

    {
        echo '#!/bin/bash'
        echo 'export TEST_VARIABLE="Config Called"'
    } >"$INVENTORY_CONFIG"
}

test__load_config_cfg_exists() {
    unset TEST_VARIABLE
    _load_config "$INVENTORY_CONFIG"
    assertEquals "${TEST_VARIABLE}" "Config Called"
    unset TEST_VARIABLE
    unset INVENTORY_INTERVAL
}

test__load_config_cfg_does_not_exist_bash() {
    unset INVENTORY_INTERVAL
    _load_config "does_not_exist.cfg"
    assertEquals "${INVENTORY_INTERVAL}" "14400"
    unset INVENTORY_INTERVAL
}

test__load_config_cfg_does_not_exist_posix() {
    unset INVENTORY_INTERVAL
    INVENTORY_INTERVAL=$(# scope effect of set -o posix
        set -o posix
        _load_config "does_not_exist.cfg"
        echo "$INVENTORY_INTERVAL"
    )
    assertEquals "${INVENTORY_INTERVAL}" "14400"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
