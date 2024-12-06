#!/bin/sh
# Copyright (C) 2019 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

: "${MK_INSTALLDIR:=""}"

if [ -n "${MK_INSTALLDIR}" ]; then
    HOMEDIR="${MK_INSTALLDIR}/runtime/controller"
    CONTROLLER_BINARY="${MK_INSTALLDIR}/package/bin/cmk-agent-ctl"
    OLD_HOMEDIR="/var/lib/cmk-agent"
else
    HOMEDIR="/var/lib/cmk-agent"
    CONTROLLER_BINARY="${BIN_DIR:-/usr/bin}/cmk-agent-ctl"
fi

usage() {
    cat >&2 <<HERE
Usage: ${0}
Create the system user 'cmk-agent' for the Checkmk agent package.
HERE
    exit 1
}

_allow_legacy_pull() {
    if [ -x "${CONTROLLER_BINARY}" ]; then
        "${CONTROLLER_BINARY}" delete-all --enable-insecure-connections
    else
        cmk-agent-ctl delete-all --enable-insecure-connections
    fi
}

_issue_legacy_pull_warning() {
    cat <<HERE

WARNING: The agent controller is operating in an insecure mode! To secure the connection run \`cmk-agent-ctl register\`.

HERE
}

_activate_single_dir() {
    [ -e "${OLD_HOMEDIR}" ] && systemctl status cmk-agent-ctl-daemon >/dev/null 2>&1 && {
        echo "Stopping cmk-agent-ctl daemon for migration of home directory."
        systemctl stop cmk-agent-ctl-daemon >/dev/null 2>&1
        restart_agent_controller_daemon="yes"
    }

    _adapt_user
    _set_user_permissions

    [ "${restart_agent_controller_daemon}" = "yes" ] && {
        # This is probably not necessary because upcoming scripts will replace the service anyways,
        # but we better leave the situation as initially found.
        echo "Starting cmk-agent-ctl daemon again."
        systemctl start cmk-agent-ctl-daemon >/dev/null 2>&1
    }
}

_adapt_user() {
    # Only change if the user really has our old home directory assigned!
    [ "$(getent passwd "cmk-agent" | cut -d: -f6)" = "/var/lib/cmk-agent" ] && {
        printf "Changing home directory of cmk-agent to %s\n" "${HOMEDIR}"
        usermod -d "${HOMEDIR}" "cmk-agent"
    }
}

_set_user_permissions() {
    # cmk-agent needs access to some files that belong to root in single directory deployment
    chown :cmk-agent "${MK_INSTALLDIR}/package/config"
    agent_controller_config="${MK_INSTALLDIR}/package/config/cmk-agent-ctl.toml"
    [ -e "${agent_controller_config}" ] && chown :cmk-agent "${agent_controller_config}"
    pre_configured_connections="${MK_INSTALLDIR}/package/config/pre_configured_connections.json"
    [ -e "${pre_configured_connections}" ] && chown :cmk-agent "${pre_configured_connections}"
}

main() {
    [ "$1" ] && usage

    # add cmk-agent system user
    echo "Creating/updating cmk-agent user account ..."
    comment="Checkmk agent system user"
    usershell="/bin/false"

    if id "cmk-agent" >/dev/null 2>&1; then
        # check that the existing user is as expected
        existing="$(getent passwd "cmk-agent")"
        existing="${existing#cmk-agent:*:*:*:}"
        expected="${comment}:${HOMEDIR}:${usershell}"
        if [ "${existing}" != "${expected}" ]; then
            echo "cmk-agent user found:  expected '${expected}'" >&2
            echo "                      but found '${existing}'" >&2
        fi
        unset existing expected
    else
        useradd \
            --comment "${comment}" \
            --system \
            --home-dir "${HOMEDIR}" \
            --no-create-home \
            --user-group \
            --shell "${usershell}" \
            "cmk-agent" || exit 1
        user_is_new="yes"
    fi

    # Create home directory manually instead of doing this on user creation,
    # because it might already exist with wrong ownership
    mkdir -p ${HOMEDIR}
    chown -R cmk-agent:cmk-agent ${HOMEDIR}

    [ -n "${MK_INSTALLDIR}" ] && _activate_single_dir

    if [ "${user_is_new}" ]; then
        _allow_legacy_pull
        _issue_legacy_pull_warning
    fi
    unset homedir comment usershell

}

main "$@"
