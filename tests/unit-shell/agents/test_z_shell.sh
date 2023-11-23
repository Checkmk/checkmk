#!/bin/bash
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#NOTE: openvms and hpux not supported
AGENT_OS_TO_TEST=("aix" "freebsd" "linux" "macosx" "netbsd" "openbsd" "openwrt" "solaris")
#NOTE: Sourcing via zsh currently not supported by any agent script!

AGENTS_TO_TEST=()
for agent_ext in "${AGENT_OS_TO_TEST[@]}"; do
    AGENTS_TO_TEST+=("${UNIT_SH_AGENTS_DIR}/check_mk_agent.${agent_ext}")
done

test_z_shell() {
    zsh -c "" >/dev/null 2>&1 || startSkipping

    for agent_path in "${AGENTS_TO_TEST[@]}"; do
        zsh "${agent_path}" >/dev/null

        assertEquals "${agent_path}" "0" "$?"
    done
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
