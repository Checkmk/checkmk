#!/bin/sh
# Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

: "${MK_INSTALLDIR:=""}"
: "${OLD_MK_VARDIR:="/var/lib/check_mk_agent"}"
: "${AGENT_USER:="cmk-agent"}"
: "${LEGACY_HOMEDIR:="/var/lib/cmk-agent"}"
: "${PREVIOUS_INSTALLATION_RECORD:="/run/check-mk-agent.previous-installation"}"

# Linux calls this script with /bin/sh, Solaris with bash. Hence, stick to POSIX sh.
# The runtime tree is walked with globs rather than with find, because Solaris has no
# "find -mindepth", and "find -exec sh -c" would run Solaris 10's legacy Bourne shell,
# which has no "${var#pattern}".

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
_migrate_runtime_dir() {
    old_runtime_dir="$1"
    new_runtime_dir="$2"

    [ -e "${old_runtime_dir}" ] && [ -e "${new_runtime_dir}" ] && [ "${old_runtime_dir}" != "${new_runtime_dir}" ] && {
        printf "Found runtime directory from previous agent installation at %s, migrating all runtime files to %s\n" "${old_runtime_dir}" "${new_runtime_dir}"

        _move_directory_contents "${old_runtime_dir}" "${new_runtime_dir}"

        # Only an emptied directory goes. Deleting whatever could not be moved
        # is the one outcome worse than leaving the old tree in place.
        rmdir "${old_runtime_dir}" 2>/dev/null
        if [ -e "${old_runtime_dir}" ]; then
            printf "Could not move everything out of %s, so it is kept. Move the rest by hand.\n" "${old_runtime_dir}"
        fi
    }
}

# Move every entry of one directory into another, descending into the
# directories the target side already has.
_move_directory_contents() (
    source_dir=$1
    target_dir=$2

    # Require real directories. Following a symlink would carry the runtime data
    # out of the tree, and the find this replaced did not follow one either.
    if [ ! -d "$source_dir" ] || [ -L "$source_dir" ] ||
        [ ! -d "$target_dir" ] || [ -L "$target_dir" ]; then
        return 1
    fi

    # "*" matches no dotfile, and every pattern stays literal when it matches
    # nothing, so each candidate is tested before it is used.
    for entry in "$source_dir"/* "$source_dir"/.[!.]* "$source_dir"/..?*; do
        # A dangling symlink is still an entry to move, and -e alone follows
        # the link and says it is not there.
        [ -e "$entry" ] || [ -L "$entry" ] || continue

        entry_target=$target_dir/${entry##*/}

        if [ ! -d "$entry_target" ]; then
            mv -f "$entry" "$entry_target"
            continue
        fi

        # The target is a directory, so it keeps the mode the package gave it
        # and the walk descends instead of moving onto it. Anything that is not
        # a directory itself would land inside it, where nothing reads it, and a
        # symlink on either side would lead out of the tree. Both stay behind,
        # and _migrate_runtime_dir reports them from what the old tree still has.
        if [ -L "$entry_target" ] || [ ! -d "$entry" ] || [ -L "$entry" ]; then
            continue
        fi

        _move_directory_contents "$entry" "$entry_target"

        # Only an emptied directory goes.
        rmdir "$entry" 2>/dev/null
    done
)

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
    # usermod refuses to change a user that has a process. Two kinds of them
    # belong to no unit that the package stops: the timer job of the Python
    # updater, which waits for the lock of the updater that installs this
    # package, and a "cmk-agent-ctl update" started by hand, which waits for the
    # installer.
    usermod -d "${new_homedir}" "${AGENT_USER}" 2>/dev/null || {
        printf "Could not change it, ending the processes of %s and trying again.\n" "${AGENT_USER}"
        pkill -TERM -u "${AGENT_USER}" 2>/dev/null
        seconds_waited=0
        while pgrep -u "${AGENT_USER}" >/dev/null 2>&1 && [ "${seconds_waited}" -lt 5 ]; do
            sleep 1
            seconds_waited=$((seconds_waited + 1))
        done

        usermod -d "${new_homedir}" "${AGENT_USER}" ||
            printf "Could not change the home directory of %s, it still points to %s. The next installation of an agent package tries again.\n" "${AGENT_USER}" "${old_homedir}"
    }

    [ "${restart_agent_controller_daemon}" = "yes" ] && {
        # This is probably not necessary because upcoming scripts will replace the service anyways,
        # but we better leave the situation as initially found.
        echo "Starting cmk-agent-ctl daemon again."
        systemctl start cmk-agent-ctl-daemon >/dev/null 2>&1
    }
}

# Print the installation directory of the package that this one replaces, if it
# is another one than this package installs to.
#
# The scripts of the previous package have removed its systemd units and its
# links in /usr/bin by the time this script runs.
_previous_installdir() {
    _recorded_installdir || _installdir_of_agent_home
}

# The pre-install scriptlet of this package saves what the previous package
# still shows at that point: the targets of its links to the agent under RPM,
# its file list under DEB. Both name <installdir>/package/bin/check_mk_agent.
_recorded_installdir() {
    [ -f "${PREVIOUS_INSTALLATION_RECORD}" ] || return 1

    recorded_installdir="$(sed -n 's|/package/bin/check_mk_agent$||p' "${PREVIOUS_INSTALLATION_RECORD}" | head -n 1)"
    # A record that outlives this run would name the wrong package next time.
    rm -f "${PREVIOUS_INSTALLATION_RECORD}"

    case "${recorded_installdir}" in
        "${MK_INSTALLDIR}") return 1 ;;
        /*) printf "%s\n" "${recorded_installdir}" ;;
        *) return 1 ;;
    esac
}

# The package creates the agent user with its home in the installation
# directory. A user that was there before the package has its home elsewhere,
# and a package without the agent controller has no user.
_installdir_of_agent_home() {
    agent_homedir="$(getent passwd "${AGENT_USER}" | cut -d: -f6)"

    case "${agent_homedir}" in
        "${MK_INSTALLDIR}/runtime/controller") return 1 ;;
        */runtime/controller) printf "%s\n" "${agent_homedir%/runtime/controller}" ;;
        *) return 1 ;;
    esac
}

main() {
    [ -n "${MK_INSTALLDIR}" ] && {
        _migrate_runtime_dir "${OLD_MK_VARDIR}" "${MK_INSTALLDIR}/runtime"
        # Neither of these two finds anything on Solaris: the legacy home
        # directory only ever exists on Linux.
        _migrate_controller_registration "${LEGACY_HOMEDIR}" "${MK_INSTALLDIR}/runtime/controller"
        _migrate_home "${LEGACY_HOMEDIR}" "${MK_INSTALLDIR}/runtime/controller"

        previous_installdir="$(_previous_installdir)" && {
            _migrate_runtime_dir "${previous_installdir}/runtime" "${MK_INSTALLDIR}/runtime"
            # The home may still name a directory that an earlier run has
            # emptied and removed, because usermod refused back then.
            _migrate_home "${previous_installdir}/runtime/controller" "${MK_INSTALLDIR}/runtime/controller"
            # The package manager kept the directory for the runtime files in it.
            rmdir "${previous_installdir}" 2>/dev/null
        }
    }

    # We're called from package manager scriptlets, where a non-zero exit code may abort the
    # whole transaction. Individual failures are reported above, but must not be fatal.
    exit 0
}

main "$@"
