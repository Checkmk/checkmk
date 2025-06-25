#!/bin/bash
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#NOTE: openvms, linux and solaris not supported
AGENT_OS_TO_TEST=("aix" "freebsd" "hpux" "macosx" "netbsd" "openbsd" "openwrt")
AGENT_OS_TO_SOURCE=("aix" "freebsd" "hpux" "macosx" "netbsd" "openbsd" "openwrt")

AGENTS_TO_TEST=()
for agent_ext in "${AGENT_OS_TO_TEST[@]}"; do
    AGENTS_TO_TEST+=("${UNIT_SH_AGENTS_DIR}/check_mk_agent.${agent_ext}")
done
AGENTS_TO_SOURCE=()
for agent_ext in "${AGENT_OS_TO_SOURCE[@]}"; do
    AGENTS_TO_SOURCE+=("${UNIT_SH_AGENTS_DIR}/check_mk_agent.${agent_ext}")
done

test_korn_shell() {
    ksh -c "" >/dev/null 2>&1 || startSkipping

    for agent_path in "${AGENTS_TO_TEST[@]}"; do
        ksh "${agent_path}" >/dev/null

        assertEquals "${agent_path}" "0" "$?"
    done
}

test_korn_shell_source() {
    ksh -c "" >/dev/null 2>&1 || startSkipping

    for agent_path in "${AGENTS_TO_SOURCE[@]}"; do
        ksh -c "MK_SOURCE_AGENT=true source '${agent_path}'"

        assertEquals "${agent_path}" "0" "$?"
    done
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
