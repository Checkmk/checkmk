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

USER_COMMENT="Checkmk agent system user"

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
    chown -R :"${GROUP_REF}" "${MK_INSTALLDIR}/package/config"
    chown -R :"${GROUP_REF}" "${MK_INSTALLDIR}/package/agent"
    chown -R "${USER_REF}":"${GROUP_REF}" "${MK_INSTALLDIR}/runtime"
}

_set_agent_controller_user_permissions() {
    # Get more finegrained access for the agent controller user only
    chown -R "${USER_REF}":"${GROUP_REF}" "${MK_INSTALLDIR}/runtime/controller"
    chown :"${GROUP_REF}" "${MK_INSTALLDIR}/package/config"
    agent_controller_config="${MK_INSTALLDIR}/package/config/cmk-agent-ctl.toml"
    [ -e "${agent_controller_config}" ] && chown :"${GROUP_REF}" "${agent_controller_config}"
    pre_configured_connections="${MK_INSTALLDIR}/package/config/pre_configured_connections.json"
    [ -e "${pre_configured_connections}" ] && chown :"${GROUP_REF}" "${pre_configured_connections}"
}

_create_user() {
    # Entirely create agent user with specified uid and gid.
    # Abort if any of the specified entities (name, uid, gid) exists before.
    # If group or user creation fails, also abort.

    # Some tests, before we touch anything
    id "${AGENT_USER}" >/dev/null 2>&1 && {
        # We can't be entirely strict about forbidding an existing user, since the rule with the "create" option
        # may remain in agent packages also on (automatic) agent updates.
        # Hence we allow a user created by us and check for the specified user setup instead.
        [ "$(getent passwd "${AGENT_USER}" | cut -d: -f5)" = "${USER_COMMENT}" ] && _check_user && return 0
        printf "User %s already exists, aborting.\n" "${AGENT_USER}"
        exit 1
    }
    [ -n "${AGENT_USER_UID}" ] && {
        id "${AGENT_USER_UID}" >/dev/null 2>&1 && {
            printf "User with uid %s already exists, aborting.\n" "${AGENT_USER_UID}"
            exit 1
        }
        uid_argument="--uid ${AGENT_USER_UID}"
    }

    if [ -n "${AGENT_USER_GID}" ]; then
        # If we have an explicit gid, we must add it before, because we can't choose on user creation
        groupadd --gid "${AGENT_USER_GID}" "${AGENT_USER}" || exit 1
        group_argument="--no-user-group --gid ${AGENT_USER_GID}"
    else
        group_argument="--user-group"
    fi

    printf "Creating %s user account ...\n" "${AGENT_USER}"
    useradd ${uid_argument} \
        ${group_argument} \
        --comment "${USER_COMMENT}" \
        --system \
        --home-dir "${HOMEDIR}" \
        --no-create-home \
        --shell "/bin/false" \
        "${AGENT_USER}" || exit 1

    _allow_legacy_pull
    _issue_legacy_pull_warning
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

_update_user() {
    # 1. If specified user exists, check if it has the specified uid. Abort if not.
    # 2. Create the specified group with gid and specified agent user name if it doesn't exist.
    # 3. If agent user exist, add it to specified group.
    # 4. If agent user doesn't exist, create it with specified uid and gid. Abort if this fails.

    [ -n "${AGENT_USER_UID}" ] && [ ! "$(id -u "${AGENT_USER}")" = "${AGENT_USER_UID}" ] && {
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

        printf "Creating %s user account ...\n" "${AGENT_USER}"
        useradd ${uid_argument} \
            ${group_argument} \
            --comment "${USER_COMMENT}" \
            --system \
            --home-dir "${HOMEDIR}" \
            --no-create-home \
            --shell "/bin/false" \
            "${AGENT_USER}" || exit 1

        _allow_legacy_pull
        _issue_legacy_pull_warning
    fi
}

_handle_user_legacy() {
    # add Checkmk agent system user
    printf "Creating/updating %s user account ...\n" "${AGENT_USER}"
    usershell="/bin/false"

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
    unset homedir usershell
}

main() {

    case "${AGENT_USER_CREATION}" in
        "auto")
            handle_user="_update_user"
            ;;
        "create")
            handle_user="_create_user"
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

    [ "${DEPLOYMENT_MODE}" = "non-root" ] && {
        "${handle_user}"
        _set_agent_user_permissions
        exit 0
    }

    "${CONTROLLER_BINARY}" --version >/dev/null 2>&1 && {
        if [ -n "${MK_INSTALLDIR}" ]; then
            "${handle_user}"
            _set_agent_controller_user_permissions
        else
            _handle_user_legacy
        fi
    }
}

main "$@"
