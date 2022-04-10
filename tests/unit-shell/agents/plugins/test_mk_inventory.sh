#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# shellcheck source=agents/plugins/mk_inventory.linux
MK_SOURCE_AGENT="yes" . "${UNIT_SH_AGENTS_DIR}/plugins/mk_inventory.linux"

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

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
