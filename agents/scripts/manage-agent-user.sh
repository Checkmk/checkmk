#!/bin/sh
# Copyright (C) 2019 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

: "${MK_INSTALLDIR:=""}"
: "${AGENT_USER:="cmk-agent"}"
: "${AGENT_USER_UID:=""}"
: "${AGENT_USER_GID:=""}"
# "auto" or "use-existing"
: "${AGENT_USER_CREATION:="auto"}"
# "root" or "non-root"
: "${DEPLOYMENT_MODE:="root"}"

if [ -n "${MK_INSTALLDIR}" ]; then
    HOMEDIR="${MK_INSTALLDIR}/runtime/controller"
    CONTROLLER_BINARY="${MK_INSTALLDIR}/package/bin/cmk-agent-ctl"
    AUTO_REGISTRATION_CONFIG="${MK_INSTALLDIR}/package/config/pre_configured_connections.json"
    REGISTERED_CONNECTIONS_PATH="${MK_INSTALLDIR}/runtime/controller/registered_connections.json"
else
    HOMEDIR="/var/lib/cmk-agent"
    CONTROLLER_BINARY="${BIN_DIR:-/usr/bin}/cmk-agent-ctl"
    AUTO_REGISTRATION_CONFIG="${HOMEDIR}/pre_configured_connections.json"
    REGISTERED_CONNECTIONS_PATH="${HOMEDIR}/registered_connections.json"
fi

USER_COMMENT="Checkmk agent system user"

usage() {
    cat >&2 <<HERE
Usage: ${0}
Create the system user '${AGENT_USER}' for the Checkmk agent package.
HERE
    exit 1
}

_set_agent_user_permissions() {
    chown -R :"${GROUP_REF}" "${MK_INSTALLDIR}/package/config"
    chown -R :"${GROUP_REF}" "${MK_INSTALLDIR}/package/agent"
    chown -R :"${GROUP_REF}" "${MK_INSTALLDIR}/package/local"
    chown -R "${USER_REF}":"${GROUP_REF}" "${MK_INSTALLDIR}/runtime"
}

_set_agent_controller_user_permissions() {
    # Get more finegrained access for the agent controller user only
    chown :"${GROUP_REF}" "${MK_INSTALLDIR}/runtime"
    chown -R "${USER_REF}":"${GROUP_REF}" "${MK_INSTALLDIR}/runtime/controller"
    chown :"${GROUP_REF}" "${MK_INSTALLDIR}/package/config"
    agent_controller_config="${MK_INSTALLDIR}/package/config/cmk-agent-ctl.toml"
    [ -e "${agent_controller_config}" ] && chown :"${GROUP_REF}" "${agent_controller_config}"
    pre_configured_connections="${MK_INSTALLDIR}/package/config/pre_configured_connections.json"
    [ -e "${pre_configured_connections}" ] && chown :"${GROUP_REF}" "${pre_configured_connections}"
}

_check_user() {
    # Confirm that name, uid, and gid exist as specified.
    # Abort if they don't.

    id -u "${AGENT_USER}" >/dev/null 2>&1 || {
        printf "Agent user %s doesn't exist, aborting.\n" "${AGENT_USER}"
        exit 1
    }

    [ -n "${AGENT_USER_UID}" ] || [ -n "${AGENT_USER_GID}" ] || return 0

    [ -n "${AGENT_USER_UID}" ] && [ ! "$(id -u "${AGENT_USER}")" = "${AGENT_USER_UID}" ] && {
        printf "Agent user %s doesn't have specified uid %s, aborting.\n" "${AGENT_USER}" "${AGENT_USER_UID}"
        exit 1
    }

    [ -n "${AGENT_USER_GID}" ] && ! id -G "${AGENT_USER}" | grep -qw "${AGENT_USER_GID}" && {
        printf "Agent user %s is not member of group %s, aborting.\n" "${AGENT_USER}" "${AGENT_USER_GID}"
        exit 1
    }

    printf "Note: Using existing agent user %s.\n" "${AGENT_USER}"
}

_nologin_shell() {
    # Set nologin as shell if available, otherwise /bin/false

    for s in /sbin/nologin /usr/sbin/nologin /bin/nologin; do
        [ -x "$s" ] && printf "%s\n" "$s" && return 0
    done
    printf "/bin/false\n"
}

_update_user() {
    # 1. If specified user exists, check if it has the specified uid. Abort if not.
    # 2. Create the specified group with gid and specified agent user name if it doesn't exist.
    # 3. If agent user exist, add it to specified group.
    # 4. If agent user doesn't exist, create it with specified uid and gid. Abort if this fails.

    [ -n "${AGENT_USER_UID}" ] && id "${AGENT_USER}" >/dev/null 2>&1 && [ ! "$(id -u "${AGENT_USER}")" = "${AGENT_USER_UID}" ] && {
        printf "Agent user %s exists, but doesn't have specified uid %s, aborting.\n" "${AGENT_USER}" "${AGENT_USER_UID}"
        exit 1
    }

    [ -n "${AGENT_USER_GID}" ] && ! getent group "${AGENT_USER_GID}" >/dev/null 2>&1 && groupadd --gid "${AGENT_USER_GID}" "${AGENT_USER}"

    if id "${AGENT_USER}" >/dev/null 2>&1; then
        [ -n "${AGENT_USER_GID}" ] && usermod -G "${AGENT_USER_GID}" "${AGENT_USER}"
    else
        [ -n "${AGENT_USER_UID}" ] && uid_argument="--uid ${AGENT_USER_UID}"

        if [ -n "${AGENT_USER_GID}" ]; then
            group_argument="--no-user-group --gid ${AGENT_USER_GID}"
        else
            group_argument="--user-group"
        fi

        usershell="$(_nologin_shell)"

        printf "Creating %s user account ...\n" "${AGENT_USER}"
        # shellcheck disable=SC2086
        useradd ${uid_argument} \
            ${group_argument} \
            --comment "${USER_COMMENT}" \
            --system \
            --home-dir "${HOMEDIR}" \
            --no-create-home \
            --shell "${usershell}" \
            "${AGENT_USER}" || exit 1
    fi
}

_handle_user_legacy() {
    # add Checkmk agent system user
    printf "Creating/updating %s user account ...\n" "${AGENT_USER}"

    usershell="$(_nologin_shell)"

    if id "${AGENT_USER}" >/dev/null 2>&1; then
        # check that the existing user is as expected
        existing="$(getent passwd "${AGENT_USER}")"
        existing="${existing#"${AGENT_USER}":*:*:*:}"
        expected="${USER_COMMENT}:${HOMEDIR}:${usershell}"
        if [ "${existing}" != "${expected}" ]; then
            printf "%s user found:  expected '%s'\n" "${AGENT_USER}" "${expected}" >&2
            printf "                but found '%s'\n" "${existing}" >&2
        fi
        unset existing expected
    else
        useradd \
            --comment "${USER_COMMENT}" \
            --system \
            --home-dir "${HOMEDIR}" \
            --no-create-home \
            --user-group \
            --shell "${usershell}" \
            "${AGENT_USER}" || exit 1
    fi

    # Create home directory manually instead of doing this on user creation,
    # because it might already exist with wrong ownership
    mkdir -p "${HOMEDIR}"
    chown -R "${AGENT_USER}":"${AGENT_USER}" "${HOMEDIR}"

    unset homedir usershell
}

_handle_legacy_pull() {
    [ -e "${REGISTERED_CONNECTIONS_PATH}" ] || {
        "${CONTROLLER_BINARY}" delete-all --enable-insecure-connections
        [ -e "${AUTO_REGISTRATION_CONFIG}" ] || {
            cat <<HERE

WARNING: The agent controller is operating in an insecure mode! To secure the connection run \`cmk-agent-ctl register\`.

HERE
        }
    }
}

main() {

    case "${AGENT_USER_CREATION}" in
        "auto")
            handle_user="_update_user"
            ;;
        "use-existing")
            handle_user="_check_user"
            ;;
        *)
            printf "Unknown value for AGENT_USER_CREATION: %s\n" "${AGENT_USER_CREATION}"
            exit 1
            ;;
    esac

    if [ -n "${AGENT_USER_UID}" ]; then
        USER_REF="${AGENT_USER_UID}"
    else
        USER_REF="${AGENT_USER}"
    fi

    if [ -n "${AGENT_USER_GID}" ]; then
        GROUP_REF="${AGENT_USER_GID}"
    else
        GROUP_REF="${AGENT_USER}"
    fi

    if [ "${DEPLOYMENT_MODE}" = "non-root" ]; then
        "${handle_user}"
        _set_agent_user_permissions
    elif "${CONTROLLER_BINARY}" --version >/dev/null 2>&1; then
        if [ -n "${MK_INSTALLDIR}" ]; then
            "${handle_user}"
            _set_agent_controller_user_permissions
        else
            _handle_user_legacy
        fi
    fi

    "${CONTROLLER_BINARY}" --version >/dev/null 2>&1 && _handle_legacy_pull
}

main "$@"
