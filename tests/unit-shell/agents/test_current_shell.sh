#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

AGENT_OS_TO_TEST=("aix" "freebsd" "linux" "openwrt" "solaris")

AGENTS_TO_TEST=()
for agent_ext in "${AGENT_OS_TO_TEST[@]}"; do
    AGENTS_TO_TEST+=("${UNIT_SH_AGENTS_DIR}/check_mk_agent.${agent_ext}")
done

readarray -t RELEVANT_AGENTS <<<"$(grep -rl "${UNIT_SH_AGENTS_DIR}" -e "CURRENT_SHELL" | sort)"

test_coverage_number_of_agents() {

    expected_agents_to_test_count="${#AGENTS_TO_TEST[@]}"
    actual_agents_to_test_count="${#RELEVANT_AGENTS[@]}"

    assertEquals "${expected_agents_to_test_count}" "${actual_agents_to_test_count}"

}

test_coverage_individual_agents() {

    index=0

    for actual_agent_path in "${RELEVANT_AGENTS[@]}"; do

        expected_agent_path="${AGENTS_TO_TEST[$index]}"

        assertEquals "${expected_agent_path}" "${actual_agent_path}"

        ((index++))

    done

}

test_set_up_current_shell() {

    for agent_path in "${AGENTS_TO_TEST[@]}"; do

        # shellcheck source=/dev/null
        MK_SOURCE_AGENT="true" source "${agent_path}"

        set_up_current_shell

        assertEquals "/bin/bash" "${CURRENT_SHELL}"

    done

}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
