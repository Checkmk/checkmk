#!/bin/sh

# This entrypoint will be executed when entering build-containers and the
# reference container in both CI and locally (using run-in-docker.sh).
# Only user actions (permission wise) can be executed.
# Everything happening in here operates in and modifies the root process of
# the then-executed command.
set -e

# Only for reference - can be set but doesn't have obvious effects on file
# accessibility. Default in containers (0022) differs from default host
# setting (002)
umask 002

if [ -n "${VERBOSE}" ]; then
    echo >&2 "\$HOME: $HOME"
    echo >&2 "\$USER: $USER"
    echo >&2 "\$UID/\$GID: $(id -u):$(id -g)"
    echo >&2 "CMD:   $*"
fi

if [ -z "${USER}" ]; then
    echo >&2 "WARNING: no \$USER set"
fi

if [ -z "${HOME}" ]; then
    echo >&2 "WARNING: no \$HOME set"
fi

# Tests
if [ -d "${HOME}/.cache" ]; then
    touch "${HOME}/.cache/testfile"
    rm "${HOME}/.cache/testfile"
else
    echo >&2 "WARNING: ${HOME}/.cache not available"
fi

if [ -d "${HOME}/.docker" ]; then
    cat "${HOME}/.docker/config.json" >/dev/null
else
    echo >&2 "WARNING: ${HOME}/.docker not available"
fi

if [ "$USER" = "jenkins" ]; then
    if [ -d "${HOME}/git_reference_clones/check_mk.git" ]; then
        cat "${HOME}/git_reference_clones/check_mk.git/config" >/dev/null
    else
        echo >&2 "WARNING: ${HOME}/git_reference_clones/check_mk.git not available"
    fi
fi

exec "$@"
