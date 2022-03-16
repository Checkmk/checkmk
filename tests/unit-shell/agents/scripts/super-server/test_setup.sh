#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

TESTEE="${UNIT_SH_AGENTS_DIR}/scripts/super-server/setup"

setUp() {
    # shellcheck source=agents/scripts/super-server/setup
    MK_SOURCE_ONLY="true" source "$TESTEE"
    :
}

test_systemd2_version() {
    _module_subfolders() {
        echo "/a/b/c/1_xinetd"
        echo "/a/b/c/0_systemd"
    }
    assertEquals $'systemd\nxinetd' "$(_available_modules)"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
