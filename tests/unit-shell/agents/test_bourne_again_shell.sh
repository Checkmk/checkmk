#!/bin/bash
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#NOTE: openvms not supported
AGENT_OS_TO_TEST=("aix" "freebsd" "hpux" "linux" "macosx" "netbsd" "openbsd" "openwrt" "solaris")
AGENT_OS_TO_SOURCE=("aix" "freebsd" "hpux" "linux" "macosx" "netbsd" "openbsd" "openwrt" "solaris")

AGENTS_TO_TEST=()
for agent_ext in "${AGENT_OS_TO_TEST[@]}"; do
    AGENTS_TO_TEST+=("${UNIT_SH_AGENTS_DIR}/check_mk_agent.${agent_ext}")
done
AGENTS_TO_SOURCE=()
for agent_ext in "${AGENT_OS_TO_SOURCE[@]}"; do
    AGENTS_TO_SOURCE+=("${UNIT_SH_AGENTS_DIR}/check_mk_agent.${agent_ext}")
done

test_bourne_again_shell() {
    for agent_path in "${AGENTS_TO_TEST[@]}"; do
        bash "${agent_path}" >/dev/null

        assertEquals "${agent_path}" "0" "$?"
    done
}

test_bourne_again_shell_source() {
    for agent_path in "${AGENTS_TO_SOURCE[@]}"; do
        bash -c "MK_SOURCE_AGENT=true source '${agent_path}'"

        assertEquals "${agent_path}" "0" "$?"
    done
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
