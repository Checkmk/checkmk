#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

TESTEE="${UNIT_SH_AGENTS_DIR}/scripts/manage-binaries.sh"

setUp() {
    WORK="${SHUNIT_TMPDIR}/work"
    INSTALLDIR="${WORK}/opt/checkmk/agent"
    BINDIR="${INSTALLDIR}/package/bin"
    SYMLINKDIR="${WORK}/usr/bin"
    # A PATH containing only the utilities the testee needs. This way we control whether an
    # 'alternatives' command is found, regardless of the system running the test.
    FAKE_PATH="${WORK}/path"

    mkdir -p "${BINDIR}" "${SYMLINKDIR}" "${FAKE_PATH}"

    for tool in basename ln rm; do
        ln -s "$(command -v "${tool}")" "${FAKE_PATH}/${tool}"
    done

    for binary in check_mk_agent mk-job; do
        printf '#!/bin/sh\n' >"${BINDIR}/${binary}"
        chmod +x "${BINDIR}/${binary}"
    done
}

tearDown() {
    rm -rf "${WORK}"
}

_manage_binaries() {
    PATH="${FAKE_PATH}" MK_INSTALLDIR="${INSTALLDIR}" SYMLINK_DIR="${SYMLINKDIR}" \
        /bin/sh "${TESTEE}" "$@"
}

_fake_alternatives_command() {
    cat >"${FAKE_PATH}/update-alternatives" <<EOF
#!/bin/sh
echo "\$@" >>"${WORK}/alternatives.log"
EOF
    chmod +x "${FAKE_PATH}/update-alternatives"
}

test_install_creates_symlinks_without_alternatives() {
    _manage_binaries install
    assertEquals "exit code" "0" "$?"

    assertEquals "${BINDIR}/check_mk_agent" "$(readlink "${SYMLINKDIR}/check_mk_agent")"
    assertEquals "${BINDIR}/mk-job" "$(readlink "${SYMLINKDIR}/mk-job")"
}

test_install_replaces_leftover_symlink() {
    ln -s "/gone/check_mk_agent" "${SYMLINKDIR}/check_mk_agent"

    _manage_binaries install
    assertEquals "exit code" "0" "$?"

    assertEquals "${BINDIR}/check_mk_agent" "$(readlink "${SYMLINKDIR}/check_mk_agent")"
}

test_install_keeps_foreign_regular_file() {
    echo "not ours" >"${SYMLINKDIR}/mk-job"

    _manage_binaries install 2>/dev/null
    assertEquals "exit code" "0" "$?"

    assertEquals "not ours" "$(cat "${SYMLINKDIR}/mk-job")"
}

test_remove_deletes_symlinks() {
    _manage_binaries install

    _manage_binaries remove
    assertEquals "exit code" "0" "$?"

    assertFalse "symlink left behind" "[ -L '${SYMLINKDIR}/check_mk_agent' ]"
    assertFalse "symlink left behind" "[ -L '${SYMLINKDIR}/mk-job' ]"
}

test_remove_without_installed_symlinks() {
    _manage_binaries remove
    assertEquals "exit code" "0" "$?"
}

test_remove_without_binary_directory() {
    rm -rf "${BINDIR}"

    _manage_binaries remove
    assertEquals "exit code" "0" "$?"
}

test_multi_directory_deployment_does_nothing() {
    MK_INSTALLDIR="" PATH="${FAKE_PATH}" SYMLINK_DIR="${SYMLINKDIR}" /bin/sh "${TESTEE}" install
    assertEquals "exit code" "0" "$?"

    assertFalse "symlink created" "[ -L '${SYMLINKDIR}/check_mk_agent' ]"
}

test_install_uses_alternatives_if_available() {
    _fake_alternatives_command

    _manage_binaries install
    assertEquals "exit code" "0" "$?"

    assertFalse "symlink created despite alternatives" "[ -L '${SYMLINKDIR}/check_mk_agent' ]"
    assertEquals \
        "--install ${SYMLINKDIR}/check_mk_agent check_mk_agent ${BINDIR}/check_mk_agent 50" \
        "$(head -n1 "${WORK}/alternatives.log")"
}

test_remove_uses_alternatives_if_available() {
    _fake_alternatives_command

    _manage_binaries remove
    assertEquals "exit code" "0" "$?"

    assertEquals \
        "--remove check_mk_agent ${BINDIR}/check_mk_agent" \
        "$(head -n1 "${WORK}/alternatives.log")"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
