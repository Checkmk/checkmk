#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

AGENT_LINUX="${UNIT_SH_AGENTS_DIR}/check_mk_agent.linux"

# shellcheck source=agents/check_mk_agent.linux
MK_SOURCE_AGENT="true" source "$AGENT_LINUX"

test_labels_section() {

    cat() {
        /bin/cat <<HERE
PRETTY_NAME="Ubuntu 22.04.3 LTS"
NAME="Ubuntu"
VERSION_ID="11.11"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
VERSION_CODENAME=jammy
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=jammy
HERE
    }

    labels_section="$(section_labels)"

    assertContains "$labels_section" "<<<labels:sep(0)>>>"
    assertContains "$labels_section" '{"cmk/os_name":"Ubuntu"}'
    assertContains "$labels_section" '{"cmk/os_version":"11.11"}'
    assertContains "$labels_section" '{"cmk/os_platform":"ubuntu"}'
    assertContains "$labels_section" '{"cmk/os_type":"linux"}'

    cat() {
        /bin/cat <<HERE
NAME="AlmaLinux"
VERSION_ID="9.0"
ID="almalinux"
HERE
    }

    labels_section="$(section_labels)"

    assertContains "$labels_section" "<<<labels:sep(0)>>>"
    assertContains "$labels_section" '{"cmk/os_name":"AlmaLinux"}'
    assertContains "$labels_section" '{"cmk/os_version":"9.0"}'
    assertContains "$labels_section" '{"cmk/os_platform":"almalinux"}'
    assertContains "$labels_section" '{"cmk/os_type":"linux"}'
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
