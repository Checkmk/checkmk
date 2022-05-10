#!/bin/sh
# Copyright (C) 2019 tribe29 GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

HOMEDIR="/var/lib/cmk-agent"

usage() {
    cat >&2 <<HERE
Usage: ${0}
Create the system user 'cmk-agent' for the Checkmk agent package.
HERE
    exit 1
}

_allow_legacy_pull() {
    cmk-agent-ctl delete-all --enable-insecure-connections
}

_issue_legacy_pull_warning() {
    cat <<HERE

WARNING: The agent controller is operating in an insecure mode! To secure the connection run \`cmk-agent-ctl register\`.

HERE
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
    if [ "${user_is_new}" ]; then
        _allow_legacy_pull
        _issue_legacy_pull_warning
    fi
    chown -R cmk-agent:cmk-agent ${HOMEDIR}
    unset homedir comment usershell

}

main "$@"
