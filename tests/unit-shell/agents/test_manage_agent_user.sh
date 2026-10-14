#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

TESTEE="${UNIT_SH_AGENTS_DIR}/scripts/manage-agent-user.sh"

setUp() {
    WORK="${SHUNIT_TMPDIR}/work"
    INSTALLDIR="${WORK}/opt/checkmk/agent/default"
    # A PATH containing only fakes: the agent user exists, and chown records its calls
    # instead of changing ownership, which would need root.
    FAKE_PATH="${WORK}/path"

    mkdir -p "${INSTALLDIR}/package/bin" "${INSTALLDIR}/package/agent" \
        "${INSTALLDIR}/package/config" "${INSTALLDIR}/runtime/controller" "${FAKE_PATH}"
    touch "${INSTALLDIR}/package/agent/agent_info.json" \
        "${INSTALLDIR}/runtime/controller/registered_connections.json"

    printf '#!/bin/sh\n' >"${INSTALLDIR}/package/bin/cmk-agent-ctl"
    printf '#!/bin/sh\n' >"${FAKE_PATH}/id"
    cat >"${FAKE_PATH}/chown" <<EOF
#!/bin/sh
echo "\$@" >>"${WORK}/chown.log"
EOF
    chmod +x "${INSTALLDIR}/package/bin/cmk-agent-ctl" "${FAKE_PATH}/id" "${FAKE_PATH}/chown"
}

tearDown() {
    rm -rf "${WORK}"
}

test_root_mode_gives_the_controller_group_the_agent_directory() {
    PATH="${FAKE_PATH}" MK_INSTALLDIR="${INSTALLDIR}" /bin/sh "${TESTEE}"
    assertEquals "exit code" "0" "$?"

    assertTrue "chown calls: $(cat "${WORK}/chown.log")" \
        "grep -qxF ':cmk-agent ${INSTALLDIR}/package/agent' '${WORK}/chown.log'"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
