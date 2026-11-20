#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# migrate.sh carries the runtime state of a classic installation into the
# single-directory tree. These cases cover the move itself: the entries the
# shell's "*" does not match, a directory that exists on both sides, and the
# modes of such a directory, which the package sets and the migration must not
# undo. Further cases cover the controller registration and the home directory
# of the agent user, which the legacy layout kept in /var/lib/cmk-agent, and a
# host whose installation directory changes from one package to the next.
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
    RECORD="${WORK}/run/previous-installation"

    mkdir -p "${OLD_VARDIR}" "${RUNTIME}" "${STUBS}" "${WORK}/run"

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
[ -e '${STUBS}/agent_user_busy' ] && {
    echo "usermod: user cmk-agent is currently used by process 4711" >&2
    exit 8
}
echo "\$2" >'${STUBS}/home'
EOF
    # The agent user has a process only once a test creates
    # ${STUBS}/agent_user_busy. pkill ends it, unless the test also creates
    # ${STUBS}/ignores_term. sleep returns at once.
    cat >"${STUBS}/pgrep" <<EOF
#!/bin/sh
[ -e '${STUBS}/agent_user_busy' ]
EOF
    cat >"${STUBS}/pkill" <<EOF
#!/bin/sh
echo "pkill \$*" >>'${CALLS}'
[ -e '${STUBS}/ignores_term' ] || rm -f '${STUBS}/agent_user_busy'
EOF
    cat >"${STUBS}/sleep" <<EOF
#!/bin/sh
echo "sleep \$*" >>'${CALLS}'
EOF
    # The controller daemon runs only once a test creates ${STUBS}/daemon_running.
    cat >"${STUBS}/systemctl" <<EOF
#!/bin/sh
echo "systemctl \$*" >>'${CALLS}'
[ "\$1" = status ] && [ ! -e '${STUBS}/daemon_running' ] && exit 3
exit 0
EOF
    chmod +x "${STUBS}/getent" "${STUBS}/usermod" "${STUBS}/systemctl" \
        "${STUBS}/pgrep" "${STUBS}/pkill" "${STUBS}/sleep"
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
        PREVIOUS_INSTALLATION_RECORD="${RECORD}" \
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

test_processes_of_the_agent_user_are_left_alone_when_the_home_directory_changes() {
    # CMK-42019
    printf '%s\n' "${LEGACY_HOME}" >"${STUBS}/home"

    _migrate >/dev/null

    assertEquals "pkill calls" "0" "$(grep -c '^pkill' "${CALLS}")"
}

test_home_directory_changes_although_the_agent_user_has_a_process() {
    # CMK-42019
    # usermod refuses to change a user that has a process. The timer job of the
    # Python updater and a "cmk-agent-ctl update" started by hand are such
    # processes, and neither belongs to a unit that the package stops.
    printf '%s\n' "${LEGACY_HOME}" >"${STUBS}/home"
    printf '' >"${STUBS}/agent_user_busy"

    _migrate >/dev/null 2>&1

    assertEquals "home of the agent user" "${CONTROLLER}" "$(cat "${STUBS}/home")"
}

test_home_directory_that_cannot_be_changed_is_reported() {
    # CMK-42019
    printf '%s\n' "${LEGACY_HOME}" >"${STUBS}/home"
    printf '' >"${STUBS}/agent_user_busy"
    printf '' >"${STUBS}/ignores_term"

    output="$(_migrate 2>/dev/null)"

    assertContains "output" "${output}" \
        "Could not change the home directory of cmk-agent, it still points to ${LEGACY_HOME}."
}

test_exit_code_is_zero_when_the_home_directory_cannot_be_changed() {
    # CMK-42019
    printf '%s\n' "${LEGACY_HOME}" >"${STUBS}/home"
    printf '' >"${STUBS}/agent_user_busy"
    printf '' >"${STUBS}/ignores_term"

    _migrate >/dev/null 2>&1

    assertEquals "exit code" "0" "$?"
}

test_waiting_for_the_processes_of_the_agent_user_is_limited() {
    # CMK-42019
    # The script runs inside a package transaction, which must not hang on a
    # process that ignores the signal.
    printf '%s\n' "${LEGACY_HOME}" >"${STUBS}/home"
    printf '' >"${STUBS}/agent_user_busy"
    printf '' >"${STUBS}/ignores_term"

    _migrate >/dev/null 2>&1

    assertEquals "seconds waited" "5" "$(grep -c '^sleep 1$' "${CALLS}")"
}

test_controller_daemon_is_started_again_when_the_home_directory_cannot_be_changed() {
    # CMK-42019
    printf '%s\n' "${LEGACY_HOME}" >"${STUBS}/home"
    printf '' >"${STUBS}/daemon_running"
    printf '' >"${STUBS}/agent_user_busy"
    printf '' >"${STUBS}/ignores_term"

    _migrate >/dev/null 2>&1

    assertEquals "last call" "systemctl start cmk-agent-ctl-daemon" "$(tail -n 1 "${CALLS}")"
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

# A host that has the single-directory layout already, in another installation
# directory than the one this package brings. The package manager has removed
# the files of the previous package and kept what the agent wrote at runtime.
_previous_installation() {
    PREVIOUS="${WORK}/opt/checkmk/agent-old/default"
    rm -rf "${OLD_VARDIR}"
    mkdir -p "${PREVIOUS}/runtime/controller" "${PREVIOUS}/runtime/cmk-update-agent"
    printf '{"push": {}}\n' >"${PREVIOUS}/runtime/controller/registered_connections.json"
    printf '{"source": {}}\n' >"${PREVIOUS}/runtime/controller/agent-update-state.json"
    printf 'host_secret\n' >"${PREVIOUS}/runtime/cmk-update-agent/cmk-update-agent.state"
    printf '%s\n' "${PREVIOUS}/runtime/controller" >"${STUBS}/home"
}

test_runtime_files_of_a_previous_installation_directory_are_migrated() {
    # CMK-42087
    _previous_installation

    _migrate >/dev/null

    assertEquals "content of the registry" '{"push": {}}' \
        "$(cat "${CONTROLLER}/registered_connections.json")"
    assertEquals "content of the update state" '{"source": {}}' \
        "$(cat "${CONTROLLER}/agent-update-state.json")"
    assertEquals "content of the Python updater's state" "host_secret" \
        "$(cat "${RUNTIME}/cmk-update-agent/cmk-update-agent.state")"
    assertFalse "the previous installation directory survived" "[ -e '${PREVIOUS}' ]"
}

test_home_directory_follows_the_installation_directory() {
    # CMK-42087
    _previous_installation

    _migrate >/dev/null

    assertEquals "home of the agent user" "${CONTROLLER}" "$(cat "${STUBS}/home")"
}

test_runtime_files_are_migrated_while_usermod_refuses() {
    # CMK-42087
    _previous_installation
    printf '' >"${STUBS}/agent_user_busy"
    printf '' >"${STUBS}/ignores_term"

    _migrate >/dev/null 2>&1

    assertEquals "exit code" "0" "$?"
    assertEquals "content of the registry" '{"push": {}}' \
        "$(cat "${CONTROLLER}/registered_connections.json")"
}

test_home_in_a_removed_installation_directory_is_corrected() {
    # CMK-42087
    # What a run leaves behind in which usermod refused: the files are in the
    # new tree, and the home still names the directory they came from.
    _previous_installation
    printf '' >"${STUBS}/agent_user_busy"
    printf '' >"${STUBS}/ignores_term"
    _migrate >/dev/null 2>&1
    rm "${STUBS}/agent_user_busy" "${STUBS}/ignores_term"

    _migrate >/dev/null

    assertEquals "home of the agent user" "${CONTROLLER}" "$(cat "${STUBS}/home")"
}

test_home_outside_an_installation_directory_is_left_alone() {
    # CMK-42087
    # The rule "Customize agent package" can name a user the package does not
    # create, and such a user has whatever home its administrator gave it.
    rm -rf "${OLD_VARDIR}"
    printf '%s\n' "${WORK}/var/home/monitoring" >"${STUBS}/home"
    before="$(_snapshot)"

    _migrate >/dev/null

    assertEquals "the files changed" "${before}" "$(_snapshot)"
    assertFalse "a command was called" "[ -s '${CALLS}' ]"
}

# An agent user that was there before the package. Its home says nothing about
# the installation directory.
_agent_user_with_its_own_home() {
    printf '%s\n' "${WORK}/var/home/monitoring" >"${STUBS}/home"
}

# What the pre-install scriptlet of an RPM package saves: the targets of the
# link in /etc/alternatives and of the one in /usr/bin, which the previous
# package has not removed at that point.
_record_previous_installation() {
    printf '%s\n' "${PREVIOUS}/package/bin/check_mk_agent" /etc/alternatives/check_mk_agent >"${RECORD}"
}

test_runtime_files_are_migrated_for_a_user_with_its_own_home() {
    # CMK-42087
    _previous_installation
    _agent_user_with_its_own_home
    _record_previous_installation

    _migrate >/dev/null

    assertEquals "content of the registry" '{"push": {}}' \
        "$(cat "${CONTROLLER}/registered_connections.json")"
}

test_own_home_of_the_agent_user_is_kept_when_the_installation_directory_changes() {
    # CMK-42087
    _previous_installation
    _agent_user_with_its_own_home
    _record_previous_installation

    _migrate >/dev/null

    assertEquals "home of the agent user" "${WORK}/var/home/monitoring" "$(cat "${STUBS}/home")"
}

test_runtime_files_are_migrated_when_the_record_is_a_file_list() {
    # CMK-42087
    # What the preinst of a DEB package saves: the output of "dpkg-query -L",
    # which lists the files of the previous package at that point.
    _previous_installation
    _agent_user_with_its_own_home
    cat >"${RECORD}" <<EOF
/.
/opt
${PREVIOUS}
${PREVIOUS}/package
${PREVIOUS}/package/bin
${PREVIOUS}/package/bin/check_mk_agent
${PREVIOUS}/package/bin/cmk-agent-ctl
${PREVIOUS}/package/scripts/migrate.sh
EOF

    _migrate >/dev/null

    assertEquals "content of the registry" '{"push": {}}' \
        "$(cat "${CONTROLLER}/registered_connections.json")"
}

test_runtime_files_are_migrated_without_an_agent_user() {
    # CMK-42087
    # A package without the agent controller creates no user.
    _previous_installation
    rm "${STUBS}/home"
    _record_previous_installation

    _migrate >/dev/null

    assertEquals "content of the Python updater's state" "host_secret" \
        "$(cat "${RUNTIME}/cmk-update-agent/cmk-update-agent.state")"
}

test_record_of_the_previous_installation_is_removed() {
    # CMK-42087
    _previous_installation
    _record_previous_installation

    _migrate >/dev/null

    assertFalse "the record survived" "[ -e '${RECORD}' ]"
}

test_stale_home_is_corrected_by_a_package_for_the_same_directory() {
    # CMK-42087
    # The home still names the directory that an earlier run could not move it
    # away from, and the package that replaces the one in this directory
    # records this directory.
    _previous_installation
    printf '%s\n' "${INSTALLDIR}/package/bin/check_mk_agent" >"${RECORD}"

    _migrate >/dev/null

    assertEquals "home of the agent user" "${CONTROLLER}" "$(cat "${STUBS}/home")"
}

test_runtime_files_are_migrated_when_the_record_names_no_installation_directory() {
    # CMK-42087
    # The record is empty when the previous package was removed rather than
    # replaced: its links are gone, and dpkg lists no files of it.
    _previous_installation
    : >"${RECORD}"

    _migrate >/dev/null

    assertEquals "content of the registry" '{"push": {}}' \
        "$(cat "${CONTROLLER}/registered_connections.json")"
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
