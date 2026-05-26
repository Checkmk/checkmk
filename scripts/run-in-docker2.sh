#!/usr/bin/env bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Runs attached command in a Docker container.

set -e -o pipefail

# some style settings defined here
txtRed=$'\e[41m'
txtGreen=$'\e[32m'
txtBlue=$'\e[34m'
resetColor=$'\e[0m'

print_red() {
    printf "%s%s%s\n" "${txtRed}" "$1" "${resetColor}"
}

print_green() {
    printf "%s%s%s\n" "${txtGreen}" "$1" "${resetColor}"
}

print_blue() {
    printf "%s%s%s\n" "${txtBlue}" "$1" "${resetColor}"
}

print_debug() {
    if [[ $DEBUG_MODE -gt 0 ]]; then
        print_blue "    $1"
    fi
}

help() {
    cat <<'EOF'
Usage: ./run-in-docker2.sh <CMD> [OPTION...]

Default value of CMD is "bash"
If nothing is specified then the available env variables resolve to their defaults

Custom images can be used like:
    IMAGE_ALIAS=IMAGE_SLES_15SP7 run-in-docker2.sh <CMD>
    IMAGE_ID=ubuntu-22.04:latest run-in-docker2.sh <CMD>
    IMAGE_ID=artifacts.lan.tribe29.com:4000/ubuntu-22.04:master-latest run-in-docker2.sh <CMD>

Run a specific Pytest and stay inside the container after the test completed for further debugging:
    run-in-docker2.sh --keep-going TEST_FILTER="-k test_apache_restart_trigger" tests/run_tests.sh test-integration

Options:
    -h, --help                    Show this message and exit
    -d, --debug                   Emit debugging messages
    --mount-host-cache-folder     Mount ~/.cache into the container
    --enable-dind                 Enable Docker-in-Docker usage
    --keep-going                  Drop into an interactive shell after the command finishes (even on error)

ENVIRONMENT VARIABLES
    CONTAINER_NAME      Defaults to "klaus-$(basename "$(pwd)")-<RANDOM_NUMBER>"
    CPU_LIMITATION      Defaults to "--cpus=8"
    DOCKER_ENV_ARGS     Defaults to "-e POD_LABEL='my-local-pod'"
    DOCKER_RUN_ADDOPTS  Additional docker run option args, no default value
    IMAGE_ALIAS         No default
    IMAGE_ID            Defaults to "artifacts.lan.tribe29.com:4000/ubuntu-24.04:master-latest"
    KEEP_GOING          When set, drop into an interactive shell after the command finishes (even on error)
    MEMORY_LIMITATION   Defaults to "--memory=24g"
    TERMINAL_FLAG       Defaults to "--interactive --tty"
    VERBOSE             Emit debugging messages, valid values to enable are [1, true, True, TRUE]
EOF
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -d | --debug)
            DEBUG_MODE=1
            print_blue "Debug mode activated"
            shift
            ;;
        --mount-host-cache-folder)
            MOUNT_HOST_CACHE_FOLDER=1
            shift
            ;;
        --enable-dind)
            ENABLE_DIND=1
            shift
            ;;
        --keep-going)
            KEEP_GOING=1
            shift
            ;;
        -h | --help)
            help
            exit 0
            ;;
        --* | -*)
            echo "Unknown option $1"
            echo "Run './run-in-docker2.sh --help' for available options." >&2
            exit 1
            ;;
        *)
            break
            ;;
    esac
done

if [[ "${VERBOSE,,}" =~ ^(true|1)$ || "${DEBUG,,}" =~ ^(true|1)$ ]]; then
    DEBUG_MODE=1
    print_debug "Activated debug mode via env flag"
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
print_debug "SCRIPT_DIR: ${SCRIPT_DIR}"

CHECKOUT_ROOT="$(git rev-parse --show-toplevel)"
print_debug "CHECKOUT_ROOT: ${CHECKOUT_ROOT}"

# in case of worktrees $CHECKOUT_ROOT might not contain the actual repository clone
GIT_COMMON_DIR="$(realpath "$(git rev-parse --git-common-dir)")"
print_debug "GIT_COMMON_DIR: ${GIT_COMMON_DIR}"

# Strip leading VAR=value env assignments from the actual command
ENV_ARGS=()
while [[ $# -gt 0 && "$1" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; do
    ENV_ARGS+=("$1")
    shift
done
print_debug "ENV_ARGS: ${ENV_ARGS}"

CMD_ARGS=("$@")
print_debug "CMD_ARGS: ${CMD_ARGS}"

# Build export statements with safe quoting so values with spaces/specials works
EXPORT_STMTS=""
for kv in "${ENV_ARGS[@]}"; do
    varname="${kv%%=*}"
    varval="${kv#*=}"
    EXPORT_STMTS+="export $(printf '%s=%q' "$varname" "$varval"); "
done
print_debug "EXPORT_STMTS: ${EXPORT_STMTS}"

if [[ ${#CMD_ARGS[@]} -eq 0 ]]; then
    print_red "No commands given, fallback to default shell (bash)"
    CMD_ARGS=("bash")
fi

: "${CONTAINER_USER:="root"}"
print_debug "CONTAINER_USER: ${CONTAINER_USER}"

: "${TERMINAL_FLAG:="$([ -t 0 ] && echo ""--interactive --tty"" || echo "")"}"
print_debug "TERMINAL_FLAG: ${TERMINAL_FLAG}"

# all pods of Jenkins as of now use 8 CPUs maximum
# except for building CMK distro package, which is using up to 12 CPUs
: "${CPU_LIMITATION:="--cpus=8"}"
print_debug "CPU_LIMITATION: ${CPU_LIMITATION}"

# all pods of Jenkins as of now use 16GB RAM
# except for test-plugins which requires 20GB
# building a CMK distro package is using 32GB if built from scratch
: "${MEMORY_LIMITATION:="--memory=24g"}"
print_debug "MEMORY_LIMITATION: ${MEMORY_LIMITATION}"

# by setting "POD_LABEL" the container behaves like a real k8s pod in Jenkins
DOCKER_ENV_ARGS="${DOCKER_ENV_ARGS:+$DOCKER_ENV_ARGS }-e POD_LABEL=my-local-pod -e USER"
print_debug "DOCKER_ENV_ARGS: ${DOCKER_ENV_ARGS}"

: "${CONTAINER_NAME:="$(basename "$(pwd)")-klaus-$(shuf -i 42-100 -n 1)"}"
print_debug "CONTAINER_NAME: ${CONTAINER_NAME}"

: "${IMAGE_ID:="$(
    if [ -n "${IMAGE_ALIAS}" ]; then
        "${CHECKOUT_ROOT}"/buildscripts/docker_image_aliases/resolve.py "${IMAGE_ALIAS}"
    else
        echo "artifacts.lan.tribe29.com:4000/ubuntu-24.04:master-latest"
    fi
)"}"
if [ -n "${IMAGE_ALIAS}" ]; then
    print_debug "IMAGE_ALIAS: ${IMAGE_ALIAS}"
fi
print_debug "IMAGE_ID: ${IMAGE_ID}"

DOCKER_MOUNT_ARGS="-v ${CHECKOUT_ROOT}:/checkmk"
# with "--mount" the execution of binaries is not allowed and can not be changed
# use "--tmpfs" instead
# see https://docs.docker.com/engine/storage/tmpfs/#options-for---tmpfs
if [[ $MOUNT_HOST_CACHE_FOLDER -gt 0 ]]; then
    print_debug "Mounting ${HOME}/.cache into container"
    DOCKER_MOUNT_ARGS="${DOCKER_MOUNT_ARGS} -v ${HOME}/.cache:/${CONTAINER_USER}/.cache"
else
    print_debug "Using 10GB tmpfs for ~/.cache inside container"
    DOCKER_MOUNT_ARGS="${DOCKER_MOUNT_ARGS} --tmpfs /${CONTAINER_USER}/.cache:exec,size=10g,mode=777"
fi

if [[ $ENABLE_DIND -gt 0 ]]; then
    print_debug "Mounting ~/.docker into container"
    DOCKER_MOUNT_ARGS="${DOCKER_MOUNT_ARGS} -v ${HOME}/.docker:/${CONTAINER_USER}/.docker"
    DOCKER_MOUNT_ARGS="${DOCKER_MOUNT_ARGS} -v "/var/run/docker.sock:/var/run/docker.sock""
fi

# we can not afford 8GB of tmpfs on a user machine for /git to have everything always clean
# this is where the dirty bootstrap_container.sh script enters the stage to safe us
# DOCKER_MOUNT_ARGS="${DOCKER_MOUNT_ARGS} --tmpfs /git:exec,size=8g,mode=777"

# do not mount group into the container, some tests will interact (create+delete) groups
# and thereby fail if the group is mounted as "ro". Not limiting it might be a security risk
# So simply don't sync it
# -v "/etc/group:/etc/group:ro" \
# -v "/etc/passwd:/etc/passwd:ro" \
print_debug "DOCKER_MOUNT_ARGS: ${DOCKER_MOUNT_ARGS}"

if [ -n "${DOCKER_RUN_ADDOPTS}" ]; then
    print_debug "DOCKER_RUN_ADDOPTS: ${DOCKER_RUN_ADDOPTS}"
fi

BOOTSTRAP_INNER_SCRIPT='/checkmk/scripts/bootstrap_container.sh /checkmk/. /git;'

# Inner script: export vars, run command (if any)
if [[ ${#CMD_ARGS[@]} -gt 0 ]]; then
    INNER_SCRIPT="${BOOTSTRAP_INNER_SCRIPT} ${EXPORT_STMTS}"'"$@";'
else
    INNER_SCRIPT="${BOOTSTRAP_INNER_SCRIPT} ${EXPORT_STMTS}"
fi

# stay in an interactive shell so the exported vars remain available for further manual commands
# CMD_ARGS are forwarded via bash -c ... -- ARGS so no re-quoting is needed.
if [[ -n "${KEEP_GOING:-}" ]]; then
    print_red "Don't get blinded by the lights, simply move on"
    print_debug "KEEP_GOING: ${KEEP_GOING}"
    INNER_SCRIPT+="exec bash"
fi

print_debug "Entering container now"

# shellcheck disable=SC2086
docker run -a stdout -a stderr \
    --rm \
    --name ${CONTAINER_NAME} \
    ${TERMINAL_FLAG} \
    --ulimit nofile=8192:8192 \
    ${CPU_LIMITATION} \
    ${MEMORY_LIMITATION} \
    --workdir /git \
    -v ${CHECKOUT_ROOT}:/checkmk \
    -v /home/$(whoami)/.cmk-credentials:/${CONTAINER_USER}/.cmk-credentials:ro \
    --group-add="$(getent group docker | cut -d: -f3)" \
    ${DOCKER_MOUNT_ARGS} \
    ${DOCKER_ENV_ARGS} \
    ${DOCKER_RUN_ADDOPTS} \
    "${IMAGE_ID}" \
    bash -c "${INNER_SCRIPT}" -- "${CMD_ARGS[@]}"
