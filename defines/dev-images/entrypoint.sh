#!/bin/sh

set -e

if [ -z "$USER" ]; then
    echo >&2 "Error: no \$USER set"
    exit 1
fi

if [ -z "$HOME" ]; then
    echo >&2 "Error: no \$HOME set"
    exit 1
fi

umask 002

mkdir -p "${HOME}/.cache/"

if [ -n "${VERBOSE}" ]; then
    echo >&2 "\$HOME: $HOME"
    echo >&2 "\$USER: $USER"
    echo >&2 "\$UID/\$GID: $(id -u):$(id -g)"
    echo >&2 "CMD:   $*"
fi

exec "$@"
