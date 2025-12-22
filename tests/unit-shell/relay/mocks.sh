#!/bin/bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Mock Functions for install_relay.sh Tests
#
# This file provides mock implementations of all external commands called by
# install_relay.sh. Each mock function:
#   - Records its call in the MOCK_CALLS array (with function name and arguments)
#   - If MOCK_CALLS_FILE is set, also appends to that file (for subshell tracking)
#   - Returns success (exit code 0) by default
#   - Delegates to the real command when appropriate (for builtins and safe operations)
#
# Usage:
#   source mocks.sh
#   # Use mocked functions
#   loginctl enable-linger user
#   # Check calls
#   echo "Total calls: ${#MOCK_CALLS[@]}"
#   for call in "${MOCK_CALLS[@]}"; do echo "$call"; done
#
# For subshell tracking:
#   MOCK_CALLS_FILE=$(mktemp)
#   export MOCK_CALLS_FILE
#   # ... run code in subshell ...
#   mapfile -t MOCK_CALLS < "$MOCK_CALLS_FILE"

# Shared list to track all mock function calls
MOCK_CALLS=()

# Helper function to record a call
_record_call() {
    local call="$*"
    MOCK_CALLS+=("$call")
    # Also write to file if tracking across subshells
    if [ -n "${MOCK_CALLS_FILE:-}" ]; then
        # Create parent directory if needed
        /bin/mkdir -p "$(dirname "$MOCK_CALLS_FILE")" 2>/dev/null || true
        builtin echo "$call" >>"$MOCK_CALLS_FILE"
    fi
}
export -f _record_call

# Mock: basename - Get script name
# shellcheck disable=SC2317
basename() {
    _record_call "basename $*"
    /usr/bin/basename "$@"
}
export -f basename

# Mock: command - Check if command exists
# shellcheck disable=SC2317
command() {
    _record_call "command $*"
    # Default: pretend all commands exist
    if [[ "$1" == "-v" ]]; then
        echo "/usr/bin/$2"
        return 0
    fi
    builtin command "$@"
}
export -f command

# Mock: loginctl - Enable user lingering
# shellcheck disable=SC2317
loginctl() {
    _record_call "loginctl $*"
    return 0
}
export -f loginctl

# Mock: podman - Container operations
# shellcheck disable=SC2317
podman() {
    _record_call "podman $*"
    # Simulate successful podman operations
    case "$1" in
        volume)
            if [[ "$2" == "exists" ]]; then
                return 1 # Volume doesn't exist, will be created
            fi
            ;;
        pull | tag | run)
            return 0
            ;;
    esac
    return 0
}
export -f podman

# Mock: systemctl - Systemd service management
# shellcheck disable=SC2317
systemctl() {
    _record_call "systemctl $*"
    return 0
}
export -f systemctl

# Mock: mkdir - Create directories
# shellcheck disable=SC2317
mkdir() {
    _record_call "mkdir $*"
    /bin/mkdir "$@"
}
export -f mkdir

# Mock: chmod - Set file permissions
# shellcheck disable=SC2317
chmod() {
    _record_call "chmod $*"
    /bin/chmod "$@"
}
export -f chmod

# Mock: cat - Write files (usually via heredocs)
# shellcheck disable=SC2317
cat() {
    _record_call "cat $*"
    /bin/cat "$@"
}
export -f cat

# Mock: echo - Output messages
# shellcheck disable=SC2317
echo() {
    _record_call "echo $*"
    builtin echo "$@"
}
export -f echo

# Mock: date - Format timestamps
# shellcheck disable=SC2317
date() {
    _record_call "date $*"
    builtin echo "2025-01-01 12:00:00"
}
export -f date

# Mock: sleep - Wait/delay
# shellcheck disable=SC2317
sleep() {
    _record_call "sleep $*"
    # Don't actually sleep in tests
    return 0
}
export -f sleep

# shellcheck disable=SC2317
info() { :; }
export -f info

# shellcheck disable=SC2317
warn() { :; }
export -f warn

# shellcheck disable=SC2317
err() { echo "$@" >&2; }
export -f err

# shellcheck disable=SC2317
die() {
    err "$@"
    exit 1
}
export -f die

# Mock: get_euid - Return effective user ID
# Returns 1000 (non-root) by default for tests
# shellcheck disable=SC2317
get_euid() {
    echo 1000
}
export -f get_euid
