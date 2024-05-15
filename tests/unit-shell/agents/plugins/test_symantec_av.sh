#!/bin/bash
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# shellcheck source=agents/plugins/kaspersky_av
MK_SOURCE_ONLY=true source "${UNIT_SH_PLUGINS_DIR}/symantec_av"

test_root_owned() {

    # owned by root:root, other users can't write
    file_info1="-rwxrwxr-x 1 root root 0 Jan  1 00:00 /opt/kaspersky/kav4fs/bin/kav4fs-control"
    assertTrue "root_owned \"$file_info1\""

    # owned by root:root, other users can write
    file_info2="-rwxrwxrwx 1 root root 0 Jan  1 00:00 /opt/kaspersky/kav4fs/bin/kav4fs-control"
    assertFalse "root_owned \"$file_info2\""

    # owned by root:test, group can write
    file_info3="-rwxrwxr-x 1 root test 0 Jan  1 00:00 /opt/kaspersky/kav4fs/bin/kav4fs-control"
    assertFalse "root_owned \"$file_info3\""

    # owned by root:test, group can't write
    file_info4="-rwxr-xr-x 1 root test 0 Jan  1 00:00 /opt/kaspersky/kav4fs/bin/kav4fs-control"
    assertTrue "root_owned \"$file_info4\""

    # not owned by root
    file_info5="-rwxr-xr-x 1 test test 0 Jan  1 00:00 /opt/kaspersky/kav4fs/bin/kav4fs-control"
    root_owned "$file_info5"
    assertFalse "root_owned \"$file_info5\""

}

# shellcheck disable=SC1090 # Can't follow
. "$UNIT_SH_SHUNIT2"
