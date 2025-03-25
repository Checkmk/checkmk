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

_migrate_runtime_dir() {
    old_runtime_dir="$1"
    new_runtime_dir="$2"

    [ -e "${old_runtime_dir}" ] && [ -e "${new_runtime_dir}" ] && [ "${old_runtime_dir}" != "${new_runtime_dir}" ] && {
        printf "Found runtime directory from previous agent installation at %s, migrating all runtime files to %s\n" "${old_runtime_dir}" "${new_runtime_dir}"
        mv -f "${old_runtime_dir}"/* "${new_runtime_dir}"
        rm -r "${old_runtime_dir}"
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
