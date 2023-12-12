#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# shellcheck source=agents/plugins/mk_tsm
MK_SOURCE_ONLY=true source "${UNIT_SH_PLUGINS_DIR}/mk_tsm"

test_export_env_resilient_against_command_injection() {

    # whatch out: this will fail if you change "while..do..done <<< input" to "input | while..do..done" in the plugin.
    export_extracted_env " dsmserv _=/usr/bin/dsmserv FOO=bar DSMSERV_CONFIG=/foobar;fail_if_this_is_a_command LC__FASTMSG=true"
    assertEquals "/foobar;fail_if_this_is_a_command" "${DSMSERV_CONFIG}"

}

# shellcheck disable=SC1090 # Can't follow
. "$UNIT_SH_SHUNIT2"
