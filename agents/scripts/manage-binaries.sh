#!/bin/sh
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

: "${MK_INSTALLDIR:=""}"
: "${SYMLINK_DIR:="/usr/bin"}"

# Linux calls this script with /bin/sh, Solaris with bash. Hence, stick to POSIX sh.

usage() {
    cat >&2 <<HERE
Usage ${0} install|remove

Commands:
  install      Make all binaries found in this Checkmk agent package available as command by
               registering them with the 'update-alternatives' or 'alternatives' command.
               On systems providing neither of them, plain symlinks are created instead.
  remove       Remove installed symlinks.
HERE
    exit 1
}

_install_symlinks() {
    _setup_alternatives_command
    _remove_old_agent_controller
    for binary in "${MK_INSTALLDIR}"/package/bin/*; do
        [ -f "${binary}" ] || continue
        name=$(basename "${binary}")
        [ -n "${ALTERNATIVES}" ] && {
            # We don't make use of the priority, but it's mandatory, so we only choose an arbitrarily chosen 50.
            "${ALTERNATIVES}" --install "${SYMLINK_DIR}/${name}" "${name}" "${binary}" 50
            # If the alternative is already existing, we have to activate our binary path in place explicitly.
            # Otherwise this call will just pass silently.
            "${ALTERNATIVES}" --set "${name}" "${binary}"
            continue
        }
        [ -e "${SYMLINK_DIR}/${name}" ] && [ ! -L "${SYMLINK_DIR}/${name}" ] && {
            printf "Can't create symlink at %s: A file already exists and is not a symlink.\n" \
                "${SYMLINK_DIR}/${name}" >&2
            continue
        }
        # The downside to the plain symlink is that we lose the information from another agent installtion entirely.
        # Since we currently don't support multiple agent installations, this is OK for the moment.
        # Force the link, it may be left over from a previous installation, possibly dangling.
        ln -sf "${binary}" "${SYMLINK_DIR}/${name}"
    done
}

_setup_alternatives_command() {
    [ -n "${MK_INSTALLDIR}" ] || {
        # Only in single directory deployment we can be sure that all binaries under package/bin are our own,
        # and run echo the alternatives command on all of them.
        # Since this script is also executed in multi directory deployment, we exit silently here.
        exit 0
    }

    if command -v update-alternatives >/dev/null 2>&1; then
        ALTERNATIVES="update-alternatives"
    elif command -v alternatives >/dev/null 2>&1; then
        ALTERNATIVES="alternatives"
    else
        ALTERNATIVES=""
    fi
}

_remove_old_agent_controller() {
    [ -e "${SYMLINK_DIR}/cmk-agent-ctl" ] && [ ! -L "${SYMLINK_DIR}/cmk-agent-ctl" ] && {
        printf "Removing leftover agent controller at %s\n" "${SYMLINK_DIR}/cmk-agent-ctl"
        rm -f "${SYMLINK_DIR}/cmk-agent-ctl"
    }
}

_remove_symlinks() {
    _setup_alternatives_command
    for binary in "${MK_INSTALLDIR}"/package/bin/*; do
        [ -f "${binary}" ] || continue
        name=$(basename "${binary}")
        [ -n "${ALTERNATIVES}" ] && {
            # This will auto-uninstall the entire alternative if this is the last active link
            "${ALTERNATIVES}" --remove "${name}" "${binary}"
            continue
        }
        # This might also uninstall a symlink that came from another agent installation and that replaced ours.
        # Since we currently don't support multiple agent installations, this is OK for the moment.
        [ -L "${SYMLINK_DIR}/${name}" ] && rm "${SYMLINK_DIR}/${name}"
    done
}

main() {
    [ "$1" = "-v" ] && {
        shift
        set -x
    }

    case "$1" in
        install)
            _install_symlinks
            ;;
        remove)
            _remove_symlinks
            ;;
        *)
            usage
            ;;
    esac

    # We're called from package manager scriptlets, where a non-zero exit code may abort the
    # whole transaction. Individual failures are reported above, but must not be fatal.
    exit 0
}

main "$@"
