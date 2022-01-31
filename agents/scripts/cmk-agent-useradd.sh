#!/bin/sh
# Copyright (C) 2019 tribe29 GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

usage() {
    cat <<HERE
Usage: ${0} --create
Create the system user 'cmk-agent' for the Checkmk agent package.
HERE
    exit 1
}

main() {
    [ "${1}" = "--create" ] || usage

    # add cmk-agent system user
    echo "Creating/updating cmk-agent user account..."
    homedir="/var/lib/cmk-agent"
    comment="Checkmk agent system user"
    usershell="/bin/false"

    if id "cmk-agent" >/dev/null 2>&1; then
        # check that the existing user is as expected
        existing="$(getent passwd "cmk-agent")"
        existing="${existing#cmk-agent:*:*:*:}"
        expected="${comment}:${homedir}:${usershell}"
        if [ "${existing}" != "${expected}" ]; then
            echo "cmk-agent user found:  expected '${expected}'" >&2
            echo "                      but found '${existing}'" >&2
            echo "Refusing to install with unexpected user properties." >&2
            exit 1
        fi
        unset existing expected
    else
        useradd \
            --comment "${comment}" \
            --system \
            --home-dir "${homedir}" \
            --no-create-home \
            --shell "${usershell}" \
            "cmk-agent" || exit 1
    fi

    # Create home directory manually instead of doing this on user creation,
    # because it might already exist with wrong ownership
    mkdir -p ${homedir}
    chown -R cmk-agent:cmk-agent ${homedir}

    unset homedir comment usershell

}

main "$@"
