#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# migrate.sh carries the runtime state of a classic installation into the
# single-directory tree. These cases cover the move itself: the entries the
# shell's "*" does not match, a directory that exists on both sides, and the
# modes of such a directory, which the package sets and the migration must not
# undo.
#
# The script also runs on Solaris, from an SVR4 postinstall script. The last two
# cases cover what that adds: another shell, and an exit code that must not
# abort the package transaction.

TESTEE="${UNIT_SH_AGENTS_DIR}/scripts/migrate.sh"

setUp() {
    WORK="${SHUNIT_TMPDIR}/work"
    OLD_VARDIR="${WORK}/var/lib/check_mk_agent"
    INSTALLDIR="${WORK}/opt/checkmk/agent/default"
    RUNTIME="${INSTALLDIR}/runtime"
    STUBS="${WORK}/stubs"

    mkdir -p "${OLD_VARDIR}" "${RUNTIME}" "${STUBS}"

    # The classic layout has these, and so does the new one, which is what
    # makes them the interesting case.
    mkdir -p "${OLD_VARDIR}/cache" "${OLD_VARDIR}/job"

    # The package ships these empty and with these modes, and the migration has
    # to leave them that way. 0751 on runtime and runtime/job lets mk-job
    # traverse to runtime/job/<user>; the rest is closed to others (werk 22168).
    mkdir -p "${RUNTIME}/cache" "${RUNTIME}/job"
    chmod 0751 "${RUNTIME}" "${RUNTIME}/job"
    chmod 0750 "${RUNTIME}/cache"

    # The agent user is left alone: a getent that finds nobody makes the home
    # directory step return before it reaches usermod.
    for stub in getent usermod systemctl; do
        printf '#!/bin/sh\nexit 1\n' >"${STUBS}/${stub}"
        chmod +x "${STUBS}/${stub}"
    done
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
        "$1" "${TESTEE}"
}

test_hidden_file_is_moved() {
    printf 'kept\n' >"${OLD_VARDIR}/.hidden"

    _migrate >/dev/null

    assertTrue "hidden file did not arrive" "[ -f '${RUNTIME}/.hidden' ]"
    assertEquals "content of the hidden file" "kept" "$(cat "${RUNTIME}/.hidden")"
}

test_directory_on_both_sides_is_merged() {
    printf 'from the old tree\n' >"${OLD_VARDIR}/cache/old_entry"
    printf 'already here\n' >"${RUNTIME}/cache/new_entry"

    _migrate >/dev/null

    assertTrue "the old entry did not arrive" "[ -f '${RUNTIME}/cache/old_entry' ]"
    assertTrue "the entry of the new tree is gone" "[ -f '${RUNTIME}/cache/new_entry' ]"
    assertFalse "the old runtime directory survived" "[ -e '${OLD_VARDIR}' ]"
}

test_directory_on_both_sides_keeps_the_mode_of_the_package() {
    # The classic layout had these open to others. Moving the directory itself
    # would replace the one the package created and bring 0755 along.
    chmod 0755 "${OLD_VARDIR}/cache"
    printf 'from the old tree\n' >"${OLD_VARDIR}/cache/old_entry"

    _migrate >/dev/null

    assertEquals "mode of runtime/cache" "750" "$(stat -c '%a' "${RUNTIME}/cache")"
    assertEquals "mode of runtime" "751" "$(stat -c '%a' "${RUNTIME}")"
}

test_a_nested_directory_on_both_sides_is_merged_as_well() {
    mkdir -p "${OLD_VARDIR}/cache/sub" "${RUNTIME}/cache/sub"
    printf 'from the old tree\n' >"${OLD_VARDIR}/cache/sub/old_entry"
    printf 'already here\n' >"${RUNTIME}/cache/sub/new_entry"

    _migrate >/dev/null

    assertTrue "the nested old entry did not arrive" "[ -f '${RUNTIME}/cache/sub/old_entry' ]"
    assertTrue "the nested entry of the new tree is gone" "[ -f '${RUNTIME}/cache/sub/new_entry' ]"
}

test_dangling_symlink_is_moved() {
    # Its target does not exist, so a test for the entry itself has to look at
    # the link rather than at what it points to.
    ln -s /nowhere/at/all "${OLD_VARDIR}/dangling"

    _migrate >/dev/null

    assertTrue "the dangling symlink did not arrive" "[ -L '${RUNTIME}/dangling' ]"
    assertFalse "the old runtime directory survived" "[ -e '${OLD_VARDIR}' ]"
}

test_file_is_not_moved_into_a_directory_of_its_name() {
    # mv would put the file inside the directory, at runtime/plain/plain,
    # where nothing reads it. It has to stay behind and be reported instead.
    printf 'content\n' >"${OLD_VARDIR}/plain"
    mkdir -p "${RUNTIME}/plain"

    _migrate >/dev/null 2>&1

    assertFalse "the file was moved into the directory" "[ -f '${RUNTIME}/plain/plain' ]"
    assertTrue "the file was not kept" "[ -f '${OLD_VARDIR}/plain' ]"
}

test_what_cannot_be_moved_is_kept() {
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
    # The SVR4 postinstall script of the Solaris package calls this, and a
    # non-zero exit code there can abort the whole pkgadd transaction.
    mkdir -p "${OLD_VARDIR}/spool"
    printf 'precious\n' >"${OLD_VARDIR}/spool/precious"
    printf 'in the way\n' >"${RUNTIME}/spool"

    _migrate >/dev/null 2>&1

    assertEquals "exit code" "0" "$?"
}

test_migration_runs_under_korn_shell() {
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
