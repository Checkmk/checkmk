#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# migrate.sh carries the runtime state of a classic installation into the
# single-directory tree. These cases cover the move itself: the entries the
# shell's "*" does not match, a directory that exists on both sides, and the
# modes of such a directory, which the package sets and the migration must not
# undo. Further cases cover the controller registration and the home directory
# of the agent user, which the legacy layout kept in /var/lib/cmk-agent.
#
# The script also runs on Solaris, from an SVR4 postinstall script. The last two
# cases cover what that adds: another shell, and an exit code that must not
# abort the package transaction.

TESTEE="${UNIT_SH_AGENTS_DIR}/scripts/migrate.sh"

setUp() {
    # CMK-40622 AC8
    WORK="${SHUNIT_TMPDIR}/work"
    OLD_VARDIR="${WORK}/var/lib/check_mk_agent"
    INSTALLDIR="${WORK}/opt/checkmk/agent/default"
    RUNTIME="${INSTALLDIR}/runtime"
    CONTROLLER="${RUNTIME}/controller"
    LEGACY_HOME="${WORK}/var/lib/cmk-agent"
    STUBS="${WORK}/stubs"
    CALLS="${WORK}/calls"

    mkdir -p "${OLD_VARDIR}" "${RUNTIME}" "${STUBS}"

    # The classic layout has these, and so does the new one, which is what
    # makes them the interesting case.
    mkdir -p "${OLD_VARDIR}/cache" "${OLD_VARDIR}/job"

    # The package ships these empty and with these modes, and the migration has
    # to leave them that way. 0751 on runtime and runtime/job lets mk-job
    # traverse to runtime/job/<user>; the rest is closed to others (werk 22168).
    mkdir -p "${RUNTIME}/cache" "${RUNTIME}/job" "${CONTROLLER}"
    chmod 0751 "${RUNTIME}" "${RUNTIME}/job"
    chmod 0750 "${RUNTIME}/cache" "${CONTROLLER}"

    # The agent user exists only once a test writes its home to ${STUBS}/home.
    # Until then getent finds nobody, and the home directory step returns
    # before it reaches usermod. usermod writes the new home there, so a second
    # run sees what the first one did.
    cat >"${STUBS}/getent" <<EOF
#!/bin/sh
[ -e '${STUBS}/home' ] || exit 2
echo "cmk-agent:x:999:999::\$(cat '${STUBS}/home'):/bin/false"
EOF
    cat >"${STUBS}/usermod" <<EOF
#!/bin/sh
echo "usermod \$*" >>'${CALLS}'
echo "\$2" >'${STUBS}/home'
EOF
    # The controller daemon runs only once a test creates ${STUBS}/daemon_running.
    cat >"${STUBS}/systemctl" <<EOF
#!/bin/sh
echo "systemctl \$*" >>'${CALLS}'
[ "\$1" = status ] && [ ! -e '${STUBS}/daemon_running' ] && exit 3
exit 0
EOF
    chmod +x "${STUBS}/getent" "${STUBS}/usermod" "${STUBS}/systemctl"
}

tearDown() {
    rm -rf "${WORK}"
}

_migrate() {
    _migrate_with /bin/sh
}

_migrate_with() {
    PATH="${STUBS}:${PATH}" \
        MK_INSTALLDIR="${INSTALLDIR}" \
        OLD_MK_VARDIR="${OLD_VARDIR}" \
        LEGACY_HOMEDIR="${LEGACY_HOME}" \
        "$1" "${TESTEE}"
}

_snapshot() {
    find "${WORK}/opt" "${WORK}/var" -printf '%p %y %m %s\n' | sort
}

test_nothing_is_migrated_without_installdir() {
    # CMK-40622 AC1
    printf 'from the old tree\n' >"${OLD_VARDIR}/cache/old_entry"
    mkdir -p "${LEGACY_HOME}"
    printf '{}\n' >"${LEGACY_HOME}/registered_connections.json"
    printf '%s\n' "${LEGACY_HOME}" >"${STUBS}/home"
    before="$(_snapshot)"

    env -u MK_INSTALLDIR \
        PATH="${STUBS}:${PATH}" \
        OLD_MK_VARDIR="${OLD_VARDIR}" \
        LEGACY_HOMEDIR="${LEGACY_HOME}" \
        /bin/sh "${TESTEE}" >/dev/null

    assertEquals "the files changed" "${before}" "$(_snapshot)"
    assertFalse "a command was called" "[ -s '${CALLS}' ]"
}

test_nothing_to_migrate() {
    # CMK-40622 AC2
    rm -rf "${OLD_VARDIR}"
    printf '%s\n' "${CONTROLLER}" >"${STUBS}/home"
    before="$(_snapshot)"

    _migrate >/dev/null

    assertEquals "the files changed" "${before}" "$(_snapshot)"
    assertFalse "a command was called" "[ -s '${CALLS}' ]"
}

test_custom_old_vardir_is_migrated() {
    # CMK-40622 AC6
    OLD_VARDIR="${WORK}/srv/agent-state"
    mkdir -p "${OLD_VARDIR}"
    printf 'from the custom tree\n' >"${OLD_VARDIR}/entry"

    _migrate >/dev/null

    assertEquals "content of the moved entry" "from the custom tree" "$(cat "${RUNTIME}/entry")"
    assertFalse "the custom directory survived" "[ -e '${OLD_VARDIR}' ]"
}

test_controller_registration_is_migrated() {
    # CMK-40621 AC2, CMK-40622 AC4
    mkdir -p "${LEGACY_HOME}"
    printf '{"push": {}}\n' >"${LEGACY_HOME}/registered_connections.json"
    printf '' >"${LEGACY_HOME}/allow-legacy-pull"

    _migrate >/dev/null

    assertEquals "content of the registry" '{"push": {}}' "$(cat "${CONTROLLER}/registered_connections.json")"
    assertTrue "the legacy pull marker did not arrive" "[ -f '${CONTROLLER}/allow-legacy-pull' ]"
    assertFalse "the legacy home directory survived" "[ -e '${LEGACY_HOME}' ]"
}

test_home_directory_of_the_agent_user_changes() {
    # CMK-40622 AC5
    printf '%s\n' "${LEGACY_HOME}" >"${STUBS}/home"

    _migrate >/dev/null

    assertEquals "usermod call" "usermod -d ${CONTROLLER} cmk-agent" "$(grep '^usermod' "${CALLS}")"
}

test_running_controller_daemon_is_stopped_around_usermod() {
    # CMK-40622 AC5
    printf '%s\n' "${LEGACY_HOME}" >"${STUBS}/home"
    printf '' >"${STUBS}/daemon_running"

    _migrate >/dev/null

    assertEquals "calls" \
        "systemctl status cmk-agent-ctl-daemon
systemctl stop cmk-agent-ctl-daemon
usermod -d ${CONTROLLER} cmk-agent
systemctl start cmk-agent-ctl-daemon" \
        "$(cat "${CALLS}")"
}

test_second_run_changes_nothing() {
    # CMK-40622 AC7
    printf 'from the old tree\n' >"${OLD_VARDIR}/cache/old_entry"
    mkdir -p "${LEGACY_HOME}"
    printf '{"push": {}}\n' >"${LEGACY_HOME}/registered_connections.json"
    printf '' >"${LEGACY_HOME}/allow-legacy-pull"
    printf '%s\n' "${LEGACY_HOME}" >"${STUBS}/home"
    _migrate >/dev/null
    after_first_run="$(_snapshot)"
    rm -f "${CALLS}"

    _migrate >/dev/null

    assertEquals "the files changed" "${after_first_run}" "$(_snapshot)"
    assertFalse "a command was called" "[ -s '${CALLS}' ]"
}

test_hidden_file_is_moved() {
    # CMK-40621 AC2, CMK-40622 AC3
    printf 'kept\n' >"${OLD_VARDIR}/.hidden"

    _migrate >/dev/null

    assertTrue "hidden file did not arrive" "[ -f '${RUNTIME}/.hidden' ]"
    assertEquals "content of the hidden file" "kept" "$(cat "${RUNTIME}/.hidden")"
}

test_directory_on_both_sides_is_merged() {
    # CMK-40621 AC2, CMK-40622 AC3
    printf 'from the old tree\n' >"${OLD_VARDIR}/cache/old_entry"
    printf 'already here\n' >"${RUNTIME}/cache/new_entry"

    _migrate >/dev/null

    assertTrue "the old entry did not arrive" "[ -f '${RUNTIME}/cache/old_entry' ]"
    assertTrue "the entry of the new tree is gone" "[ -f '${RUNTIME}/cache/new_entry' ]"
    assertFalse "the old runtime directory survived" "[ -e '${OLD_VARDIR}' ]"
}

test_directory_on_both_sides_keeps_the_mode_of_the_package() {
    # CMK-40621 AC2
    # The classic layout had these open to others. Moving the directory itself
    # would replace the one the package created and bring 0755 along.
    chmod 0755 "${OLD_VARDIR}/cache"
    printf 'from the old tree\n' >"${OLD_VARDIR}/cache/old_entry"

    _migrate >/dev/null

    assertEquals "mode of runtime/cache" "750" "$(stat -c '%a' "${RUNTIME}/cache")"
    assertEquals "mode of runtime" "751" "$(stat -c '%a' "${RUNTIME}")"
}

test_a_nested_directory_on_both_sides_is_merged_as_well() {
    # CMK-40621 AC2, CMK-40622 AC3
    mkdir -p "${OLD_VARDIR}/cache/sub" "${RUNTIME}/cache/sub"
    printf 'from the old tree\n' >"${OLD_VARDIR}/cache/sub/old_entry"
    printf 'already here\n' >"${RUNTIME}/cache/sub/new_entry"

    _migrate >/dev/null

    assertTrue "the nested old entry did not arrive" "[ -f '${RUNTIME}/cache/sub/old_entry' ]"
    assertTrue "the nested entry of the new tree is gone" "[ -f '${RUNTIME}/cache/sub/new_entry' ]"
}

test_dangling_symlink_is_moved() {
    # CMK-40621 AC2, CMK-40622 AC3
    # Its target does not exist, so a test for the entry itself has to look at
    # the link rather than at what it points to.
    ln -s /nowhere/at/all "${OLD_VARDIR}/dangling"

    _migrate >/dev/null

    assertTrue "the dangling symlink did not arrive" "[ -L '${RUNTIME}/dangling' ]"
    assertFalse "the old runtime directory survived" "[ -e '${OLD_VARDIR}' ]"
}

test_file_is_not_moved_into_a_directory_of_its_name() {
    # CMK-40621 AC2
    # mv would put the file inside the directory, at runtime/plain/plain,
    # where nothing reads it. It has to stay behind and be reported instead.
    printf 'content\n' >"${OLD_VARDIR}/plain"
    mkdir -p "${RUNTIME}/plain"

    _migrate >/dev/null 2>&1

    assertFalse "the file was moved into the directory" "[ -f '${RUNTIME}/plain/plain' ]"
    assertTrue "the file was not kept" "[ -f '${OLD_VARDIR}/plain' ]"
}

test_what_cannot_be_moved_is_kept() {
    # CMK-40621 AC2
    # A file in the new tree where the old tree has a directory: the move
    # fails, and the old data has to survive instead of being cleaned away.
    mkdir -p "${OLD_VARDIR}/spool"
    printf 'precious\n' >"${OLD_VARDIR}/spool/precious"
    printf 'in the way\n' >"${RUNTIME}/spool"

    _migrate >/dev/null 2>&1

    assertTrue "the data that could not move was deleted" \
        "[ -f '${OLD_VARDIR}/spool/precious' ]"
}

test_a_symlinked_directory_in_the_new_tree_is_not_followed() {
    # CMK-40624 AC4
    # Descending through it would carry the old runtime data out of the tree.
    mkdir -p "${WORK}/elsewhere" "${OLD_VARDIR}/linked"
    printf 'precious\n' >"${OLD_VARDIR}/linked/precious"
    ln -s "${WORK}/elsewhere" "${RUNTIME}/linked"

    _migrate >/dev/null 2>&1

    assertFalse "the migration wrote outside the runtime tree" \
        "[ -e '${WORK}/elsewhere/precious' ]"
    assertTrue "the data that could not move was deleted" \
        "[ -f '${OLD_VARDIR}/linked/precious' ]"
}

test_exit_code_is_zero_when_something_could_not_be_moved() {
    # CMK-40624 AC4
    # The SVR4 postinstall script of the Solaris package calls this, and a
    # non-zero exit code there can abort the whole pkgadd transaction.
    mkdir -p "${OLD_VARDIR}/spool"
    printf 'precious\n' >"${OLD_VARDIR}/spool/precious"
    printf 'in the way\n' >"${RUNTIME}/spool"

    _migrate >/dev/null 2>&1

    assertEquals "exit code" "0" "$?"
}

test_migration_runs_under_korn_shell() {
    # CMK-40624 AC4
    # Solaris resolves "sh" to ksh93. There is no Solaris 10 Bourne shell to
    # test against here, so ksh is the closest stand-in available.
    ksh -c "" >/dev/null 2>&1 || startSkipping

    printf 'from the old tree\n' >"${OLD_VARDIR}/cache/old_entry"
    printf 'kept\n' >"${OLD_VARDIR}/.hidden"

    _migrate_with ksh >/dev/null 2>&1

    assertEquals "exit code" "0" "$?"
    assertTrue "the old entry did not arrive" "[ -f '${RUNTIME}/cache/old_entry' ]"
    assertTrue "hidden file did not arrive" "[ -f '${RUNTIME}/.hidden' ]"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
