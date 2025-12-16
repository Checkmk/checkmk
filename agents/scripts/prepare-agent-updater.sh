#!/bin/sh
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This script will care for the proper file structure and access rights to operate cmk-update-agent,
# which will run under the agent controller user starting with Checkmk 2.5.
#
# Required environment variables to run this migration script:
#
# MK_INSTALLDIR: Indicator and root folder for single directory deployment
#
# MK_BIN, MK_CONFDIR, MK_VARDIR: Relevant for multi directory deployment if MK_INSTALLDIR is unset
#
# AGENT_CONTROLLER_USER: If set and agent controller is actually available, the agent updater will run under this user.
#  Note that this user is identical to the agent user in single directory deployment, even if the agent controller is not active.
#
# DEPLOYMENT_MODE - root or non-root. Relevant for access rights of folders created within this script.
#  Note that non-root deployment mode only exists in single directory deployment.

_migrate_files() {
    if [ -n "${MK_INSTALLDIR}" ]; then
        NEW_STATE_FOLDER="${MK_INSTALLDIR}/runtime/cmk-update-agent"
        NEW_LOG_FOLDER="${MK_INSTALLDIR}/runtime/log/cmk-update-agent"
        runtime_folder="${MK_INSTALLDIR}/runtime"
    else
        NEW_STATE_FOLDER="${MK_VARDIR}/cmk-update-agent"
        # Note: Not using MK_LOGDIR, which defaults to /var/log/check_mk_agent, for logging. Not before, not now.
        NEW_LOG_FOLDER="${MK_VARDIR}/log/cmk-update-agent"
        runtime_folder="${MK_VARDIR}"
    fi

    state_file="cmk-update-agent.state"
    [ -e "${NEW_STATE_FOLDER}/${state_file}" ] || {
        if [ -e "${runtime_folder}/${state_file}" ]; then # 2.4
            old_state_path="${runtime_folder}/${state_file}"
        elif [ -e "/etc/${state_file}" ]; then # pre 2.4
            old_state_path="/etc/${state_file}"
        fi
        [ -n "${old_state_path}" ] && {
            mkdir -p "${NEW_STATE_FOLDER}"
            mv "${old_state_path}"* "${NEW_STATE_FOLDER}" # Move state file and backup
        }
    }

    log_file="cmk-update-agent.log"
    [ -e "${NEW_LOG_FOLDER}/${log_file}" ] || {
        [ -e "${runtime_folder}/${log_file}" ] && {
            mkdir -p "${NEW_LOG_FOLDER}"
            mv "${runtime_folder}/${log_file}"* "${NEW_LOG_FOLDER}" # Move current and rotated logs
        }
    }
}

_set_access_rights() {
    # Create these directories if not yet existing.
    # cmk-update-agent is able to create them by itself in certain situations, but we need them anyways.
    mkdir -p "${NEW_STATE_FOLDER}"
    mkdir -p "${NEW_LOG_FOLDER}"

    [ "${DEPLOYMENT_MODE}" = "root" ] && {
        # Root deployment with no agent controller. cmk-update-agent will also run under root, no permissions needed.
        _agent_controller_active || return

        # When reaching this point, we are running under root with agent controller.
        # cmk-update-agent will run under the agent controller user and needs access to certain resources.
        if [ -n "${MK_INSTALLDIR}" ]; then
            # Single directory deployment.
            # These resources are not yet available after 'manage_agent_user.sh' run.
            chown :"${AGENT_CONTROLLER_USER}" "${MK_INSTALLDIR}/package/agent"
            chown :"${AGENT_CONTROLLER_USER}" "${MK_INSTALLDIR}/package/agent/agent_info.json"
            chown :"${AGENT_CONTROLLER_USER}" "${MK_INSTALLDIR}/package/config/cmk-update-agent.cfg"
        else
            # Multi directory deployment
            # Directories are generally accessible, but access to files is restricted.
            chown :"${AGENT_CONTROLLER_USER}" "${MK_VARDIR}/agent_info.json"
            chown :"${AGENT_CONTROLLER_USER}" "${MK_CONFDIR}/cmk-update-agent.cfg"
        fi
    }
    # When reaching this point, cmk-update-agent will either run under the agent controller user or under the agent user,
    # Which can both be identified by AGENT_CONTROLLER_USER.
    # cmk-update-agent must own its resources and be able to create it.
    chown -R "${AGENT_CONTROLLER_USER}":"${AGENT_CONTROLLER_USER}" "${NEW_STATE_FOLDER}"
    chown -R "${AGENT_CONTROLLER_USER}":"${AGENT_CONTROLLER_USER}" "${NEW_LOG_FOLDER}"
}

_agent_controller_active() {
    [ -n "${AGENT_CONTROLLER_USER}" ] || return 1

    [ -n "${MK_INSTALLDIR}" ] && {
        "${MK_INSTALLDIR}/package/bin/cmk-agent-ctl" -V >/dev/null 2>&1 && return 0
        return 1
    }

    "${MK_BIN}/cmk-agent-ctl" -V >/dev/null 2>&1 && return 0
    return 1
}

main() {
    _migrate_files # Also sets NEW_STATE_FOLDER and NEW_LOG_FOLDER
    _set_access_rights
}

main "$@"
