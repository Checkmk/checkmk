#!/bin/sh
# Copyright (C) 2019 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

: "${MK_INSTALLDIR:=""}"
: "${AGENT_USER:="cmk-agent"}"
: "${AGENT_USER_UID:=""}"
: "${AGENT_USER_GID:=""}"
# "auto" or "create" or "use-existing"
: "${AGENT_USER_CREATION:="auto"}"
# "root" or "non-root"
: "${DEPLOYMENT_MODE:="root"}"

if [ -n "${MK_INSTALLDIR}" ]; then
    HOMEDIR="${MK_INSTALLDIR}/runtime/controller"
    CONTROLLER_BINARY="${MK_INSTALLDIR}/package/bin/cmk-agent-ctl"
else
    HOMEDIR="/var/lib/cmk-agent"
    CONTROLLER_BINARY="${BIN_DIR:-/usr/bin}/cmk-agent-ctl"
fi

usage() {
    cat >&2 <<HERE
Usage: ${0}
Create the system user '${AGENT_USER}' for the Checkmk agent package.
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

_set_agent_user_permissions() {
    chown -R :"${AGENT_USER}" "${MK_INSTALLDIR}/package/config"
    chown -R :"${AGENT_USER}" "${MK_INSTALLDIR}/package/agent"
    chown -R "${AGENT_USER}":"${AGENT_USER}" "${MK_INSTALLDIR}/runtime"
}

_set_agent_controller_user_permissions() {
    # Get more finegrained access for the agent controller user only
    chown :"${AGENT_USER}" "${MK_INSTALLDIR}/package/config"
    agent_controller_config="${MK_INSTALLDIR}/package/config/cmk-agent-ctl.toml"
    [ -e "${agent_controller_config}" ] && chown :"${AGENT_USER}" "${agent_controller_config}"
    pre_configured_connections="${MK_INSTALLDIR}/package/config/pre_configured_connections.json"
    [ -e "${pre_configured_connections}" ] && chown :"${AGENT_USER}" "${pre_configured_connections}"
}

_add_user() {
    # add Checkmk agent system user
    printf "Creating/updating %s user account ...\n" "${AGENT_USER}"
    comment="Checkmk agent system user"
    usershell="/bin/false"

    if id "${AGENT_USER}" >/dev/null 2>&1; then
        # check that the existing user is as expected
        existing="$(getent passwd "${AGENT_USER}")"
        existing="${existing#"${AGENT_USER}":*:*:*:}"
        expected="${comment}:${HOMEDIR}:${usershell}"
        if [ "${existing}" != "${expected}" ]; then
            printf "%s user found:  expected '%s'\n" "${AGENT_USER}" "${expected}" >&2
            printf "                but found '%s'\n" "${existing}" >&2
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
            "${AGENT_USER}" || exit 1
        user_is_new="yes"
    fi

    # Create home directory manually instead of doing this on user creation,
    # because it might already exist with wrong ownership
    mkdir -p "${HOMEDIR}"
    chown -R "${AGENT_USER}":"${AGENT_USER}" "${HOMEDIR}"

    if [ "${user_is_new}" ]; then
        _allow_legacy_pull
        _issue_legacy_pull_warning
    fi
    unset homedir comment usershell

}

main() {
    [ "${DEPLOYMENT_MODE}" = "non-root" ] && {
        _add_user
        _set_agent_user_permissions
        exit 0
    }

    "${CONTROLLER_BINARY}" --version >/dev/null 2>&1 && {
        _add_user
        [ -n "${MK_INSTALLDIR}" ] && _set_agent_controller_user_permissions
    }
}

main "$@"
