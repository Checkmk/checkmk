#!/bin/sh
# Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

: "${MK_INSTALLDIR:=""}"
: "${OLD_MK_VARDIR:="/var/lib/check_mk_agent"}"
: "${AGENT_USER:="cmk-agent"}"

LEGACY_HOMEDIR="/var/lib/cmk-agent"

usage() {
    cat >&2 <<HERE
Usage: ${0}
Do necessary migration steps that are not covered by normal package manager mechanisms on agent update
HERE
    exit 1
}

# Move the old runtime tree into the new one.
#
# A directory the new tree already has keeps the one the package created, with
# the mode the package gave it, and the walk descends into it. A directory the
# new tree does not have moves whole, mode included. Moving a directory onto an
# existing one would replace it and carry the old mode along, which loses what
# werk 22168 established: the old cache is 0755 where the new one has to be
# 0750, and a collision can repeat at any depth.
#
# find walks a directory before its contents, so an entry whose parent has
# already moved is gone by the time its own turn comes - hence the test.
_migrate_runtime_dir() {
    old_runtime_dir="$1"
    new_runtime_dir="$2"

    [ -e "${old_runtime_dir}" ] && [ -e "${new_runtime_dir}" ] && [ "${old_runtime_dir}" != "${new_runtime_dir}" ] && {
        printf "Found runtime directory from previous agent installation at %s, migrating all runtime files to %s\n" "${old_runtime_dir}" "${new_runtime_dir}"

        # shellcheck disable=SC2016  # the inner shell expands these, not this one
        find "${old_runtime_dir}" -mindepth 1 -exec sh -c '
            old_dir="$1"
            new_dir="$2"
            shift 2
            for entry in "$@"; do
                # A dangling symlink is still an entry to move, and -e alone
                # follows the link and says it is not there.
                [ -e "${entry}" ] || [ -L "${entry}" ] || continue
                target="${new_dir}/${entry#"${old_dir}/"}"
                # Anything whose target is already a directory stays put: a
                # directory because the walk descends into it, a file because
                # mv would move it inside that directory, where nothing reads
                # it. What stays is reported below.
                [ -d "${target}" ] && continue
                # Whatever a failed parent left behind stays where it is, and
                # reports once through that parent rather than once per child.
                [ -d "${target%/*}" ] || continue
                mv -f "${entry}" "${target}"
            done
        ' sh "${old_runtime_dir}" "${new_runtime_dir}" {} +

        # Only the emptied directories go. A blind "rm -r" here would delete
        # whatever could not be moved, which is the one outcome worse than
        # leaving the old tree in place.
        find "${old_runtime_dir}" -depth -type d -exec rmdir {} + 2>/dev/null
        if [ -e "${old_runtime_dir}" ]; then
            printf "Could not move everything out of %s, so it is kept. Move the rest by hand.\n" "${old_runtime_dir}"
        fi
    }
}

_migrate_controller_registration() {
    old_homedir="$1"
    new_homedir="$2"

    old_legacy_pull_marker="${old_homedir}/allow-legacy-pull"
    new_legacy_pull_marker="${new_homedir}/allow-legacy-pull"
    [ -e "${old_legacy_pull_marker}" ] && [ ! -e "${new_legacy_pull_marker}" ] && {
        mv "${old_legacy_pull_marker}" "${new_legacy_pull_marker}"
    }

    old_registry="${old_homedir}/registered_connections.json"
    new_registry="${new_homedir}/registered_connections.json"
    [ -e "${old_registry}" ] && [ ! -e "${new_registry}" ] && {
        printf "Found agent controller registered connections at legacy home directory %s, migrating to %s.\n" "${old_homedir}" "${new_homedir}"
        mv "${old_registry}" "${new_homedir}"
        rm -r "${old_homedir}"
    }
}

_migrate_home() {
    old_homedir="$1"
    new_homedir="$2"

    # Only change if the user really has the legacy home directory assigned!
    [ "$(getent passwd "${AGENT_USER}" | cut -d: -f6)" = "${old_homedir}" ] || return 0

    systemctl status cmk-agent-ctl-daemon >/dev/null 2>&1 && {
        echo "Stopping cmk-agent-ctl daemon for migration of home directory."
        systemctl stop cmk-agent-ctl-daemon >/dev/null 2>&1
        restart_agent_controller_daemon="yes"
    }

    printf "Changing home directory of %s to %s\n" "${AGENT_USER}" "${new_homedir}"
    usermod -d "${new_homedir}" "${AGENT_USER}"

    [ "${restart_agent_controller_daemon}" = "yes" ] && {
        # This is probably not necessary because upcoming scripts will replace the service anyways,
        # but we better leave the situation as initially found.
        echo "Starting cmk-agent-ctl daemon again."
        systemctl start cmk-agent-ctl-daemon >/dev/null 2>&1
    }
}

main() {
    [ -n "${MK_INSTALLDIR}" ] && _migrate_runtime_dir "${OLD_MK_VARDIR}" "${MK_INSTALLDIR}/runtime"
    [ -n "${MK_INSTALLDIR}" ] && _migrate_controller_registration "${LEGACY_HOMEDIR}" "${MK_INSTALLDIR}/runtime/controller"
    [ -n "${MK_INSTALLDIR}" ] && _migrate_home "${LEGACY_HOMEDIR}" "${MK_INSTALLDIR}/runtime/controller"
}

main "$@"
