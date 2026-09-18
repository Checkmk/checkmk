#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# shellcheck source=packages/cmk-plugins/cmk/plugins/tsm/agents/mk_tsm
MK_SOURCE_ONLY=true source "${UNIT_SH_REPO_PATH}/packages/cmk-plugins/cmk/plugins/tsm/agents/mk_tsm"

# The plug-in has to keep the loop in export_extracted_env out of a subshell, which
# rules out the obvious 'sed ... | while read'. Both tests below pin that down; that
# the file stays free of bashisms is checked by shellcheck (shell=sh).

test_extracted_env_is_visible_to_the_caller() {
    unset DSMSERV_DIR

    export_extracted_env " dsmserv _=/usr/bin/dsmserv DSMSERV_DIR=/foobar_17g LC__FASTMSG=true"

    assertEquals "/foobar_17g" "${DSMSERV_DIR}"
}

test_extracted_env_is_not_executed() {
    unset DSMSERV_CONFIG

    export_extracted_env " dsmserv _=/usr/bin/dsmserv FOO=bar DSMSERV_CONFIG=/foobar;fail_if_this_is_a_command LC__FASTMSG=true"

    assertEquals "/foobar;fail_if_this_is_a_command" "${DSMSERV_CONFIG}"
}

# shellcheck disable=SC1090 # Can't follow
. "$UNIT_SH_SHUNIT2"
