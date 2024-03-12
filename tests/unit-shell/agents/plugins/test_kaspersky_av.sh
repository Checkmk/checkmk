#!/bin/bash
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# shellcheck source=agents/plugins/kaspersky_av
MK_SOURCE_ONLY=true source "${UNIT_SH_PLUGINS_DIR}/kaspersky_av"

test_only_root_can_modify() {

    # owned by root:root, other users can't write
    permissions1="-rwxrwxr-x"
    owner1="root"
    group1="root"
    assertTrue "only_root_can_modify \"$permissions1\" \"$owner1\" \"$group1\""

    # owned by root:root, other users can write
    permissions2="-rwxrwxrwx"
    owner2="root"
    group2="root"
    assertFalse "only_root_can_modify \"$permissions2\" \"$owner2\" \"$group2\""

    # owned by root:test, group can write
    permissions3="-rwxrwxr-x"
    owner3="root"
    group3="test"
    assertFalse "only_root_can_modify \"$permissions3\" \"$owner3\" \"$group3\""

    # owned by root:test, group can't write
    permissions4="-rwxr-xr-x"
    owner4="root"
    group4="test"
    assertTrue "only_root_can_modify \"$permissions4\" \"$owner4\" \"$group4\""

    # not owned by root
    permissions5="-rwxr-xr-x "
    owner5="test"
    group5="test"
    assertFalse "only_root_can_modify \"$permissions5\" \"$owner5\" \"$group5\""

}

# shellcheck disable=SC1090 # Can't follow
. "$UNIT_SH_SHUNIT2"
