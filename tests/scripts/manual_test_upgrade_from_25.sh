#!/usr/bin/env bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Manual test: a prebuilt agent package across the single-directory switch.
#
# The prebuilt agent packages moved from the classic multi-directory layout to
# /opt/checkmk/agent/default (CMK-40621). No system test covers them: the agent
# update suite runs for the pro edition only and therefore always installs a
# baked package. This script is the manual stand-in until that gap is closed.
#
# It drives three installations in a throwaway systemd container and checks the
# same things after each one:
#
#   1. the locally built package on a host that never had an agent
#   2. the released 2.5 package, after the built one was removed
#   3. the locally built package on top of that 2.5 installation
#
# Before the third installation it puts the host into the state the upgrade has
# to carry across: runtime files, a controller registration, and the
# customisation a user without a bakery applies by hand - an agent plug-in, a
# local check and a plug-in configuration. Afterwards it checks what arrived in
# the new tree and what the agent still runs.
#
# The host's own files are not moved, and the ticket does not ask for it: AC 2
# names the runtime files and the registration, "as migrate.sh does for baked
# packages", and the baked packages leave those files alone. Those six checks
# therefore report XFAIL. They are kept because the consequence is worth
# showing: a host without a bakery loses its plug-ins silently. If one of them
# ever passes, the run fails and this script needs updating.
#
# The DEB and the RPM are both covered, on x86_64, selected with --format. Only
# four things differ between them: how a package is installed, how it is
# removed, and how a version is read out of a file and out of the installed
# package. Every check below is the same for both.
#
# aarch64 is not covered. No CI runner offers it, so an installation cannot be
# tested anywhere; inspecting the built artifact is the most that is possible
# and that is QA's decision.
#
# Every check prints what it found. A failing check does not stop the run; the
# summary at the end lists the failures and the exit code reports them.

set -uo pipefail

SCRIPT_NAME="$(basename "$0" .sh)"
readonly SCRIPT_NAME
REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
readonly REPO_ROOT

# Which package to exercise. Set by --format, and everything that depends on it
# is resolved once in set_up_format().
PACKAGE_FORMAT="deb"
CONTAINER_NAME=""
IMAGE_NAME=""
BASE_IMAGE=""
BUILD_TARGET=""
BUILT_ARTIFACT=""
RELEASED_PATTERN=""

# The site that serves the released package. Every OMD site offers its own agent
# packages under this path, so any reachable 2.5 site will do.
AGENTS_URL="${AGENTS_URL:-http://localhost/v250/check_mk/agents/}"

# A package file to use instead of downloading one. For a machine with no 2.5
# site in reach: the agent packages are only served by a site, and
# download.checkmk.com needs a subscription login.
RELEASED_PACKAGE_PATH=""

# The branch that site has to serve. The scenario is the step from the classic
# layout to the single-directory one, and 2.5 is the last branch with the
# classic one.
readonly RELEASED_BRANCH="2.5.0"

# Whether step 6.1 also deletes what the package manager leaves behind. Cleaning
# gives the 2.5 installation the same starting point a fresh host has. Keeping
# it shows what a user would actually meet.
CLEAN_BETWEEN="yes"

WORK_DIR=""
CURRENT_STEP=""
AGENT_UID_BEFORE_UPGRADE=""
BUILT_DEB=""
BUILT_VERSION=""
RELEASED_DEB=""
RELEASED_VERSION=""
EXPECTED_FAILURE_REASON=""
FAILURES=()
EXPECTED_FAILURES=()
CHECKS_RUN=0

usage() {
    cat <<EOF
usage: $(basename "$0") [OPTION]...

Drive a prebuilt agent package through a fresh install of the built package, a
removal followed by a fresh install of the released one, and an upgrade back to
the built package, in a disposable systemd container. The installed layout is
checked after each step.

  -f, --format deb|rpm   which package to exercise (default: ${PACKAGE_FORMAT}).
                         deb runs on ubuntu:24.04, rpm on almalinux:10
  -k, --keep-leftovers   after removing the built package in step 6.1, leave the
                         directories the removal does not take with it
  -u, --agents-url URL   where to fetch the released package from
                         (default: ${AGENTS_URL})
  -p, --path-to-agent-package PATH
                         use this package file instead of downloading one, for
                         a machine with no 2.5 site in reach
  -h, --help             show this help

The container is named after the script and the format, is recreated on every
run and stays up afterwards for inspection. The two formats use two containers,
so a deb run and an rpm run do not disturb each other.
EOF
}

parse_options() {
    while [ $# -gt 0 ]; do
        case "$1" in
            -f | --format)
                PACKAGE_FORMAT="${2:?--format needs deb or rpm}"
                shift 2
                ;;
            -k | --keep-leftovers)
                CLEAN_BETWEEN="no"
                shift
                ;;
            -u | --agents-url)
                AGENTS_URL="${2:?--agents-url needs a URL}"
                shift 2
                ;;
            -p | --path-to-agent-package)
                RELEASED_PACKAGE_PATH="${2:?--path-to-agent-package needs a path}"
                shift 2
                ;;
            -h | --help)
                usage
                exit 0
                ;;
            *)
                echo "unknown option: $1" >&2
                usage >&2
                exit 1
                ;;
        esac
    done
}

# --- output -----------------------------------------------------------------

step() {
    printf '\n\033[1m=== %s ===\033[0m\n' "$*"
}

info() {
    printf '    %s\n' "$*"
}

# Behaviour that is known to be absent is checked inside an expected-failure
# block. Such a check is reported as XFAIL and does not fail the run. One that
# passes there fails it instead: the expectation has become stale and the script
# is the thing that needs changing.
expect_failure() {
    EXPECTED_FAILURE_REASON="$1"
}

expect_failure_end() {
    EXPECTED_FAILURE_REASON=""
}

# Report one check. $1 is the verdict, $2 what was checked, $3 what was found.
report() {
    local verdict="$1" what="$2" found="$3"
    CHECKS_RUN=$((CHECKS_RUN + 1))

    if [ -n "${EXPECTED_FAILURE_REASON}" ]; then
        if [ "${verdict}" = "pass" ]; then
            local stale="passed although it is expected to fail: ${EXPECTED_FAILURE_REASON}"
            printf '    \033[31mXPASS\033[0m %-44s %s\n' "${what}" "${found}"
            FAILURES+=("${CURRENT_STEP}: ${what} - ${stale}")
        else
            printf '    \033[33mXFAIL\033[0m %-44s %s\n' "${what}" "${found}"
            EXPECTED_FAILURES+=("${CURRENT_STEP}: ${what} - ${found}")
        fi
        return
    fi

    if [ "${verdict}" = "pass" ]; then
        printf '    \033[32mPASS\033[0m  %-44s %s\n' "${what}" "${found}"
    else
        printf '    \033[31mFAIL\033[0m  %-44s %s\n' "${what}" "${found}"
        FAILURES+=("${CURRENT_STEP}: ${what} - ${found}")
    fi
}

die() {
    printf '\n\033[31m%s\033[0m\n' "$*" >&2
    exit 1
}

# --- the one place the package format matters -------------------------------

set_up_format() {
    case "${PACKAGE_FORMAT}" in
        deb)
            BASE_IMAGE="ubuntu:24.04"
            BUILD_TARGET="//agents:check-mk-agent-deb"
            BUILT_ARTIFACT="check-mk-agent__all.deb"
            RELEASED_PATTERN='check-mk-agent_[^"<]+_all\.deb'
            ;;
        rpm)
            BASE_IMAGE="almalinux:10"
            BUILD_TARGET="//agents:check-mk-agent-rpm"
            BUILT_ARTIFACT="check-mk-agent.rpm"
            RELEASED_PATTERN='check-mk-agent-[^"<]+\.noarch\.rpm'
            ;;
        *)
            die "Unknown package format: ${PACKAGE_FORMAT}"
            ;;
    esac
    CONTAINER_NAME="${SCRIPT_NAME//_/-}-${PACKAGE_FORMAT}"
    IMAGE_NAME="${CONTAINER_NAME}:${BASE_IMAGE//:/-}"
}

# Install a package file that sits at /packages in the container. Both package
# managers resolve dependencies; the bare dpkg and rpm commands would not.
package_manager_install() {
    local deb_or_rpm="$1"
    if [ "${PACKAGE_FORMAT}" = "deb" ]; then
        # The lock timeout keeps a concurrent apt of the distribution from
        # turning into a failed installation here.
        in_container apt-get -o DPkg::Lock::Timeout=120 install -y \
            --allow-downgrades "/packages/${deb_or_rpm}"
    else
        in_container dnf install -y "/packages/${deb_or_rpm}"
    fi
}

package_manager_remove() {
    if [ "${PACKAGE_FORMAT}" = "deb" ]; then
        in_container apt-get -o DPkg::Lock::Timeout=120 purge -y check-mk-agent
    else
        in_container dnf remove -y check-mk-agent
    fi
}

# The version a package file carries, in the notation of its own format. rpm
# forbids a dash inside a version, so the released RPM reads 2.5.0_2026.10.30
# where the DEB reads 2.5.0-2026.10.30.
package_manager_file_version() {
    local deb_or_rpm="$1"
    if [ "${PACKAGE_FORMAT}" = "deb" ]; then
        in_container dpkg-deb -f "/packages/${deb_or_rpm}" Version
    else
        in_container rpm -qp --qf '%{VERSION}-%{RELEASE}' "/packages/${deb_or_rpm}"
    fi
}

package_manager_installed_version() {
    if [ "${PACKAGE_FORMAT}" = "deb" ]; then
        # shellcheck disable=SC2016  # ${Version} is dpkg-query's own format syntax
        in_container dpkg-query -W -f='${Version}' check-mk-agent 2>/dev/null
    else
        in_container rpm -q --qf '%{VERSION}-%{RELEASE}' check-mk-agent 2>/dev/null
    fi
}

# --- container --------------------------------------------------------------

in_container() {
    docker exec "${CONTAINER_NAME}" "$@"
}

# Run a command in the container and print nothing. Returns its exit code, so
# the caller decides what a failure means.
quietly_in_container() {
    docker exec "${CONTAINER_NAME}" "$@" >/dev/null 2>&1
}

# Write this process's stdin to a file in the container. $2 is the mode.
write_in_container() {
    local path="$1" mode="$2"
    docker exec -i "${CONTAINER_NAME}" sh -c "cat > '${path}' && chmod ${mode} '${path}'" ||
        die "Could not write ${path} in the container."
}

# Both images need the same three things beyond the distribution's own base:
# systemd as PID 1, because the agent's socket activation and the controller
# daemon are systemd units; the tool that prints listening sockets, for the
# port check; and "time", which mk-job calls as /usr/bin/time. The package only
# suggests it, so a minimal image does not have it and every job would fail.
build_image() {
    if [ "${PACKAGE_FORMAT}" = "deb" ]; then
        # The apt timers are masked: they start their own apt-get seconds after
        # boot and hold the dpkg lock while our first installation wants it.
        docker build -t "${IMAGE_NAME}" - <<'EOF' >/dev/null || die "Image build failed."
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl iproute2 procps systemd systemd-sysv time \
    && rm -rf /var/lib/apt/lists/* \
    && systemctl mask \
        apt-daily.service apt-daily.timer \
        apt-daily-upgrade.service apt-daily-upgrade.timer \
        unattended-upgrades.service
STOPSIGNAL SIGRTMIN+3
CMD ["/sbin/init"]
EOF
    else
        docker build -t "${IMAGE_NAME}" - <<'EOF' >/dev/null || die "Image build failed."
FROM almalinux:10
RUN dnf install -y ca-certificates curl iproute procps-ng systemd time \
    && dnf clean all
STOPSIGNAL SIGRTMIN+3
CMD ["/sbin/init"]
EOF
    fi
}

start_container() {
    docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1
    # systemd needs its own cgroup namespace and write access to the cgroup
    # hierarchy. --privileged is the short way to both inside a dev container.
    docker run -d --name "${CONTAINER_NAME}" \
        --privileged --cgroupns=host \
        -v /sys/fs/cgroup:/sys/fs/cgroup:rw \
        "${IMAGE_NAME}" >/dev/null || die "Could not start the container."

    # "degraded" is a normal outcome in a container, where units that need real
    # hardware fail. Only "initializing" and "starting" mean we have to wait.
    local waited=0 state
    while true; do
        state="$(in_container systemctl is-system-running 2>&1 | tr -d '\n')"
        case "${state}" in
            running | degraded) break ;;
        esac
        waited=$((waited + 1))
        [ "${waited}" -lt 30 ] || die "systemd did not come up: ${state}"
        sleep 1
    done
    info "systemd is ${state}"
}

# --- packages ---------------------------------------------------------------

build_package() {
    # @cmk//version defaults to the literal "UNSET", which dpkg rejects because a
    # version has to start with a digit. CI always passes the flag; so must we.
    local version
    version="$(sed -n 's/^VERSION *:= *//p' "${REPO_ROOT}/defines.make" | head -n1)"
    [ -n "${version}" ] || die "No VERSION in ${REPO_ROOT}/defines.make."
    info "building ${BUILD_TARGET} with --cmk_version=${version}"

    (cd "${REPO_ROOT}" && bazel build --cmk_version="${version}" "${BUILD_TARGET}") ||
        die "Building ${BUILD_TARGET} failed."
    local built="${REPO_ROOT}/bazel-bin/agents/${BUILT_ARTIFACT}"
    [ -f "${built}" ] || die "Built package not found at ${built}."
    cp "${built}" "${WORK_DIR}/"
    BUILT_DEB="$(basename "${built}")"
    info "built  ${BUILT_DEB} ($(du -h "${built}" | cut -f1))"
}

# Take the released package from the path the caller gave. The version is still
# read out of the package later, so a file of the wrong branch is caught just as
# a wrong site would be; only the extension is worth refusing here, because the
# error it causes further on says nothing useful.
use_local_package() {
    local given="${RELEASED_PACKAGE_PATH}"
    [ -f "${given}" ] || die "No such package file: ${given}"
    case "${given}" in
        *.deb) [ "${PACKAGE_FORMAT}" = "deb" ] || die "${given} is a deb, --format is rpm." ;;
        *.rpm) [ "${PACKAGE_FORMAT}" = "rpm" ] || die "${given} is an rpm, --format is deb." ;;
        *) die "${given} is neither a .deb nor an .rpm." ;;
    esac

    RELEASED_DEB="$(basename "${given}")"
    cp "${given}" "${WORK_DIR}/${RELEASED_DEB}" || die "Could not copy ${given}."
    info "using  ${RELEASED_DEB} ($(du -h "${given}" | cut -f1)) from ${given}"
}

download_package() {
    [ -z "${RELEASED_PACKAGE_PATH}" ] || {
        use_local_package
        return
    }

    # The file name carries the version, so read it off the index rather than
    # pinning a version that goes stale with the next site.
    # -f, so that an error page is a failure here instead of a file that only
    # dpkg finds strange later.
    local listing name
    listing="$(curl -fsS --max-time 30 "${AGENTS_URL}")" ||
        die "Could not read ${AGENTS_URL}."
    name="$(grep -oE "${RELEASED_PATTERN}" <<<"${listing}" | sort -u | head -n1)"
    [ -n "${name}" ] ||
        die "No architecture-independent ${PACKAGE_FORMAT} offered at ${AGENTS_URL}."
    curl -fsS --max-time 120 -o "${WORK_DIR}/${name}" "${AGENTS_URL}${name}" ||
        die "Downloading ${name} failed."
    RELEASED_DEB="${name}"
    info "fetched ${RELEASED_DEB} ($(du -h "${WORK_DIR}/${name}" | cut -f1))"
}

install_package() {
    local package="$1"
    info "installing ${package}"
    if ! package_manager_install "${package}" 2>&1 | sed 's/^/        /'; then
        report fail "installation of ${package}" "the package manager exited non-zero"
    fi
}

remove_package() {
    info "removing check-mk-agent"
    # A removal that did not happen leaves the next step testing something else
    # than it claims, so it is a check of its own rather than a silent step.
    if package_manager_remove 2>&1 | sed 's/^/        /'; then
        report pass "removal of check-mk-agent" "the package manager reported success"
    else
        report fail "removal of check-mk-agent" "the package manager exited non-zero"
    fi

    if [ "${CLEAN_BETWEEN}" = "yes" ]; then
        # The removal takes the package files. The runtime state, the agent user
        # and the directories the maintainer scripts created outlive it.
        info "deleting what the package manager left behind"
        in_container rm -rf \
            /opt/checkmk \
            /var/lib/check_mk_agent \
            /var/lib/cmk-agent \
            /etc/check_mk \
            /usr/lib/check_mk_agent ||
            die "Could not clean up after the previous installation."
        quietly_in_container userdel -r cmk-agent
    else
        info "keeping what the package manager left behind (--keep-leftovers)"
    fi
}

# --- what the host itself owns ----------------------------------------------

# A host without a bakery customises its agent by hand: plug-ins under
# /usr/lib/check_mk_agent/plugins, local checks next to them, and the plug-in
# configuration under /etc/check_mk. migrate.sh moves none of the three. These
# helpers put one of each in place before the upgrade, so that the output of
# the agent says whether they still run afterwards.

readonly PLUGIN_SECTION="manual_test_plugin"
readonly CFG_GREETING="hello-from-cfg"

seed_user_files() {
    info "placing a plug-in, a local check and a plug-in configuration"
    in_container mkdir -p \
        /usr/lib/check_mk_agent/plugins \
        /usr/lib/check_mk_agent/local \
        /etc/check_mk || die "Could not create the directories for the host's own files."

    # The plug-in reads its configuration and prints what it found, so one line
    # of agent output answers for both of them.
    # The configuration is sourced only when it is there: a failing "." ends a
    # POSIX shell, and the plug-in has to keep reporting its section even when
    # its configuration did not arrive, or the two checks cannot be told apart.
    write_in_container /usr/lib/check_mk_agent/plugins/manual_test_plugin 0755 <<EOF
#!/bin/sh
config="\${MK_CONFDIR:-/etc/check_mk}/manual_test.cfg"
[ -f "\${config}" ] && . "\${config}"
echo "<<<${PLUGIN_SECTION}>>>"
echo "greeting=\${MANUAL_TEST_GREETING:-unset}"
EOF

    write_in_container /etc/check_mk/manual_test.cfg 0644 <<EOF
MANUAL_TEST_GREETING=${CFG_GREETING}
EOF

    write_in_container /usr/lib/check_mk_agent/local/manual_test_local 0755 <<'EOF'
#!/bin/sh
echo '0 "Manual test local" - the local check ran'
EOF
}

# Whether the agent still runs what the host put there by hand. Called twice:
# before the upgrade it establishes the precondition, after it the acceptance
# criterion.
check_user_files_are_used() {
    local output
    output="$(in_container sh -c "check_mk_agent 2>/dev/null")"

    if grep -q "<<<${PLUGIN_SECTION}>>>" <<<"${output}"; then
        report pass "hand-installed plug-in runs" "section <<<${PLUGIN_SECTION}>>> present"
    else
        report fail "hand-installed plug-in runs" "no <<<${PLUGIN_SECTION}>>> section"
    fi

    if grep -q "greeting=${CFG_GREETING}" <<<"${output}"; then
        report pass "plug-in reads its configuration" "greeting=${CFG_GREETING}"
    else
        report fail "plug-in reads its configuration" \
            "$(grep -m1 '^greeting=' <<<"${output}" || echo "no greeting line at all")"
    fi

    if grep -q "the local check ran" <<<"${output}"; then
        report pass "hand-written local check runs" "its line is in the local section"
    else
        report fail "hand-written local check runs" "its line is missing"
    fi
}

# Where the three files ended up. The agent of the new layout reads
# package/plugins, package/config and package/local, so surviving the upgrade
# means being moved there.
check_user_files_moved() {
    local installdir="/opt/checkmk/agent/default"
    check_path file "${installdir}/package/plugins/manual_test_plugin"
    check_path file "${installdir}/package/config/manual_test.cfg"
    check_path file "${installdir}/package/local/manual_test_local"
}

# --- what migrate.sh has to carry across ------------------------------------

# migrate.sh is the whole of the upgrade promise: it moves the runtime
# directory, the controller's registration and the home directory of the agent
# user into the new tree. Nothing else in this script would notice if it did
# none of that, because the package creates the empty runtime tree either way.

readonly RUNTIME_MARKER="manual_test_runtime_marker"
readonly CACHE_MARKER="manual_test_cache_marker"
readonly LEGACY_HOMEDIR="/var/lib/cmk-agent"
readonly OLD_VARDIR="/var/lib/check_mk_agent"

seed_runtime_state() {
    info "placing runtime files and a controller registration"
    in_container mkdir -p "${OLD_VARDIR}/cache" "${LEGACY_HOMEDIR}" ||
        die "Could not create the runtime directories of the old layout."

    write_in_container "${OLD_VARDIR}/${RUNTIME_MARKER}" 0644 <<EOF
written before the upgrade
EOF
    # In a subdirectory that exists in both layouts, because migrate.sh moves
    # the entries of the old directory one by one and a collision there is the
    # case most likely to go wrong.
    write_in_container "${OLD_VARDIR}/cache/${CACHE_MARKER}" 0644 <<EOF
written before the upgrade
EOF

    # An empty object is a valid registry: every field of RegisteredConnections
    # carries a serde default. A registration against a real site would need a
    # site and a host, which this script deliberately does not have, so this
    # exercises the move rather than a round trip through the receiver.
    write_in_container "${LEGACY_HOMEDIR}/registered_connections.json" 0600 <<'EOF'
{}
EOF
    write_in_container "${LEGACY_HOMEDIR}/allow-legacy-pull" 0600 </dev/null
    in_container chown cmk-agent:cmk-agent \
        "${LEGACY_HOMEDIR}/registered_connections.json" \
        "${LEGACY_HOMEDIR}/allow-legacy-pull" ||
        die "Could not give the seeded registration to the agent user."
}

check_agent_user_home() {
    local expected="$1" home
    home="$(in_container sh -c "getent passwd cmk-agent | cut -d: -f6" | tr -d '\n')"
    if [ "${home}" = "${expected}" ]; then
        report pass "home directory of cmk-agent" "${home}"
    else
        report fail "home directory of cmk-agent" "${home:-no such user}, expected ${expected}"
    fi
}

check_runtime_state_migrated() {
    local installdir="/opt/checkmk/agent/default"
    check_path file "${installdir}/runtime/${RUNTIME_MARKER}"
    check_path file "${installdir}/runtime/cache/${CACHE_MARKER}"
    check_path file "${installdir}/runtime/controller/registered_connections.json"
    check_path file "${installdir}/runtime/controller/allow-legacy-pull"
    # migrate.sh removes both old directories once it has emptied them.
    check_path absent "${OLD_VARDIR}"
    check_path absent "${LEGACY_HOMEDIR}"
    check_agent_user_home "${installdir}/runtime/controller"
}

# --- checks -----------------------------------------------------------------

# Report whether a path exists in the container and is of the expected kind.
# $1 is one of file, dir, symlink, absent.
check_path() {
    local kind="$1" path="$2" test_flag
    case "${kind}" in
        file) test_flag="-f" ;;
        dir) test_flag="-d" ;;
        symlink) test_flag="-L" ;;
        absent) test_flag="-e" ;;
        *) die "check_path: unknown kind ${kind}" ;;
    esac

    local details
    details="$(in_container sh -c "ls -ld '${path}' 2>/dev/null | head -n1")"

    if [ "${kind}" = "absent" ]; then
        # -e follows the link and is false for a dangling one, which is exactly
        # what a removal that forgot its symlinks leaves behind. -L catches it.
        if quietly_in_container test -e "${path}" || quietly_in_container test -L "${path}"; then
            report fail "${path} is gone" "still there: ${details}"
        else
            report pass "${path} is gone" "not present"
        fi
        return
    fi

    if quietly_in_container test "${test_flag}" "${path}"; then
        report pass "${path} is a ${kind}" "${details:-present}"
    else
        report fail "${path} is a ${kind}" "${details:-not present}"
    fi
}

# Report where a symbolic link ends up. Being a link says nothing about which
# installation it serves, and that is the whole point of the layout switch.
check_symlink_resolves_into() {
    local path="$1" expected_prefix="$2" target
    target="$(in_container readlink -f "${path}" 2>/dev/null | tr -d '\n')"
    case "${target}" in
        "${expected_prefix}"*)
            report pass "${path} resolves into ${expected_prefix}" "${target}"
            ;;
        "")
            report fail "${path} resolves into ${expected_prefix}" "resolves nowhere"
            ;;
        *)
            report fail "${path} resolves into ${expected_prefix}" "${target}"
            ;;
    esac
}

check_installed_version() {
    local expected="$1" version
    version="$(package_manager_installed_version | tr -d '\n')"
    if [ -z "${expected}" ]; then
        report fail "installed package version" "no expected version known"
    elif [ "${version}" = "${expected}" ]; then
        report pass "installed package version" "${version}"
    else
        report fail "installed package version" "${version:-not installed}, expected ${expected}"
    fi
}

# An unpacked package carries the right version and has run none of its
# maintainer scripts. dpkg leaves a package in that state when it aborts, for
# instance over a conffile prompt with no terminal to answer it. rpm has no such
# half state - a transaction either completes or is rolled back - so there the
# question is only whether rpm knows the package at all.
check_package_configured() {
    if [ "${PACKAGE_FORMAT}" != "deb" ]; then
        if quietly_in_container rpm -q check-mk-agent; then
            report pass "package status" "rpm knows check-mk-agent"
        else
            report fail "package status" "rpm does not know check-mk-agent"
        fi
        return
    fi

    local status
    # shellcheck disable=SC2016  # ${Status} is dpkg-query's own format syntax
    status="$(in_container dpkg-query -W -f='${Status}' check-mk-agent 2>/dev/null)"
    if [ "${status}" = "install ok installed" ]; then
        report pass "package status" "${status}"
    else
        report fail "package status" "${status:-not known to dpkg}, expected install ok installed"
    fi
}

check_unit_active() {
    local unit="$1" state
    state="$(in_container systemctl is-active "${unit}" 2>&1 | tr -d '\n')"
    if [ "${state}" = "active" ]; then
        report pass "${unit}" "active"
    else
        report fail "${unit}" "${state}"
    fi
}

check_controller_process() {
    local processes
    processes="$(in_container sh -c "ps -o user=,args= -C cmk-agent-ctl 2>/dev/null | head -n2")"
    if [ -n "${processes}" ]; then
        report pass "cmk-agent-ctl process" "$(tr '\n' ';' <<<"${processes}" | sed 's/;$//')"
    else
        report fail "cmk-agent-ctl process" "no process found"
    fi
}

check_port_6556() {
    local listener
    listener="$(in_container sh -c "ss -ltnp 'sport = :6556' 2>/dev/null | tail -n +2")"
    if [ -n "${listener}" ]; then
        report pass "port 6556 listening" "$(tr -s ' ' <<<"${listener}" | head -n1)"
    else
        report fail "port 6556 listening" "nothing listens on 6556"
    fi
}

check_agent_output() {
    local first_line
    first_line="$(in_container sh -c "check_mk_agent 2>/dev/null | head -n1" | tr -d '\r')"
    if [ "${first_line}" = "<<<check_mk>>>" ]; then
        report pass "check_mk_agent output" "starts with <<<check_mk>>>"
    else
        report fail "check_mk_agent output" "first line: ${first_line:-<empty>}"
    fi
}

# mk-job carries its own MK_VARDIR default and never mentions MK_INSTALLDIR, so
# the build has to rewrite that line on its own. If it misses it, mk-job writes
# under /var/lib/check_mk_agent while the agent reads ${MK_VARDIR}/job in the
# new tree, and job results disappear without an error anywhere. Running a job
# and then looking for it in the agent's own output is what catches that.
check_mk_job_writes_where_the_agent_reads() {
    local vardir="$1" job_name
    job_name="manual_test_job_$(printf '%s' "${CURRENT_STEP}" | tr -cd '[:alnum:]')"

    local failure
    if ! failure="$(in_container mk-job "${job_name}" true 2>&1)"; then
        report fail "mk-job runs" "${failure:-exited non-zero}"
        return
    fi

    check_path file "${vardir}/job/root/${job_name}"

    local output
    output="$(in_container sh -c "check_mk_agent 2>/dev/null")"
    if grep -q "==> .*${job_name} <==" <<<"${output}"; then
        report pass "agent reports the job" "${job_name} is in the job section"
    else
        report fail "agent reports the job" "no record of ${job_name} in the job section"
    fi
}

# The modes of the installed tree, as agents/BUILD declares them. Werk 22168
# made these deliberate: "runtime" and "runtime/job" stay traversable so that
# mk-job can reach runtime/job/<user>, everything else under runtime is closed
# to others. On DEB a directory that already exists keeps its old mode, so the
# upgrade is where a wrong one shows up.
check_directory_modes() {
    local installdir="/opt/checkmk/agent/default"
    local entry path expected actual
    for entry in \
        "/opt/checkmk 755" \
        "/opt/checkmk/agent 755" \
        "${installdir} 755" \
        "${installdir}/package 755" \
        "${installdir}/package/bin 755" \
        "${installdir}/package/plugins 755" \
        "${installdir}/package/agent 750" \
        "${installdir}/package/config 750" \
        "${installdir}/package/local 750" \
        "${installdir}/package/scripts 750" \
        "${installdir}/runtime 751" \
        "${installdir}/runtime/job 751" \
        "${installdir}/runtime/controller 750" \
        "${installdir}/runtime/log 750" \
        "${installdir}/runtime/spool 750" \
        "${installdir}/runtime/cache 750" \
        "${installdir}/runtime/logwatch-batches 750" \
        "${installdir}/runtime/persisted 750" \
        "${installdir}/runtime/rtc_remotes 750" \
        "${installdir}/runtime/tmp 750"; do
        path="${entry% *}"
        expected="${entry##* }"
        actual="$(in_container stat -c '%a' "${path}" 2>/dev/null | tr -d '\n')"
        if [ "${actual}" = "${expected}" ]; then
            report pass "mode of ${path}" "${actual}"
        else
            report fail "mode of ${path}" "${actual:-no such directory}, expected ${expected}"
        fi
    done
}

# The agent prints the directories it reads plug-ins and local checks from.
# Files lying in the right place prove less than the agent naming it.
check_agent_reports_its_directories() {
    local installdir="/opt/checkmk/agent/default" output line
    output="$(in_container sh -c "check_mk_agent 2>/dev/null")"
    for line in "pluginsdir ${installdir}/package/plugins" \
        "localdir ${installdir}/package/local"; do
        if grep -qF "${line}" <<<"${output}"; then
            report pass "agent reports ${line%% *}" "${line#* }"
        else
            report fail "agent reports ${line%% *}" \
                "$(grep -m1 "^${line%% *} " <<<"${output}" || echo "no such line")"
        fi
    done
}

# Every binary the postinst hands to update-alternatives, not only the two the
# layout switch is most obviously about.
check_alternatives() {
    local installdir="/opt/checkmk/agent/default" binary
    for binary in check_mk_agent check_mk_caching_agent cmk-agent-ctl mk-job waitmax; do
        check_symlink_resolves_into "/usr/bin/${binary}" "${installdir}/package/bin/"
    done
}

check_agent_user_id() {
    local expected="$1" uid
    uid="$(in_container id -u cmk-agent 2>/dev/null | tr -d '\n')"
    if [ "${uid}" = "${expected}" ]; then
        report pass "uid of cmk-agent" "${uid}, unchanged"
    else
        report fail "uid of cmk-agent" "${uid:-no such user}, expected ${expected}"
    fi
}

check_controller_status() {
    local version
    version="$(in_container sh -c "cmk-agent-ctl --version 2>/dev/null" | tr -d '\n')"
    if [ -n "${version}" ]; then
        report pass "cmk-agent-ctl --version" "${version}"
    else
        report fail "cmk-agent-ctl --version" "no output"
    fi
}

# The layout half of the check block. $1 is single-dir or classic.
check_layout() {
    local layout="$1"
    local installdir="/opt/checkmk/agent/default"

    if [ "${layout}" = "single-dir" ]; then
        check_path file "${installdir}/package/bin/check_mk_agent"
        check_path file "${installdir}/package/bin/cmk-agent-ctl"
        check_path file "${installdir}/package/scripts/super-server/setup"
        check_path dir "${installdir}/runtime"
        check_path dir "${installdir}/package/config"
        # update-alternatives puts the binaries on PATH; they are no longer
        # package files of their own. Where they point is the real question.
        check_path symlink /usr/bin/check_mk_agent
        check_path symlink /usr/bin/cmk-agent-ctl
        check_symlink_resolves_into /usr/bin/check_mk_agent "${installdir}/package/bin/"
        check_symlink_resolves_into /usr/bin/cmk-agent-ctl "${installdir}/package/bin/"
    else
        check_path file /usr/bin/check_mk_agent
        check_path file /var/lib/cmk-agent/scripts/super-server/setup
        check_path dir /var/lib/check_mk_agent
        check_path dir /etc/check_mk
        if [ "${CLEAN_BETWEEN}" = "yes" ]; then
            check_path absent /opt/checkmk
        else
            # --keep-leftovers deliberately keeps the directory of the previous
            # installation, so its presence here is the request, not a finding.
            info "not checking that /opt/checkmk is gone (--keep-leftovers)"
        fi
    fi
}

# Everything that is checked after an installation.
check_installation() {
    local layout="$1" expected_version="$2"
    info "checking the ${layout} installation"
    check_installed_version "${expected_version}"
    check_package_configured
    check_layout "${layout}"
    check_unit_active cmk-agent-ctl-daemon.service
    check_unit_active check-mk-agent.socket
    check_unit_active check-mk-agent-async.service
    check_controller_process
    check_port_6556
    check_agent_output
    check_controller_status
    if [ "${layout}" = "single-dir" ]; then
        check_directory_modes
        check_agent_reports_its_directories
        check_alternatives
        check_mk_job_writes_where_the_agent_reads "/opt/checkmk/agent/default/runtime"
    else
        check_mk_job_writes_where_the_agent_reads "${OLD_VARDIR}"
    fi
}

# --- main -------------------------------------------------------------------

summarize() {
    step "Summary"
    local failed=${#FAILURES[@]}
    local expected=${#EXPECTED_FAILURES[@]}
    local passed=$((CHECKS_RUN - failed - expected))

    if [ "${failed}" -eq 0 ] && [ "${expected}" -eq 0 ]; then
        printf '    \033[32m%d checks, all passed\033[0m\n' "${CHECKS_RUN}"
    elif [ "${failed}" -eq 0 ]; then
        printf '    \033[32m%d checks, %d passed, %d expected to fail\033[0m\n' \
            "${CHECKS_RUN}" "${passed}" "${expected}"
    else
        printf '    \033[31m%d checks, %d passed, %d failed, %d expected to fail\033[0m\n' \
            "${CHECKS_RUN}" "${passed}" "${failed}" "${expected}"
        local failure
        for failure in "${FAILURES[@]}"; do
            printf '      %s\n' "${failure}"
        done
    fi

    if [ "${expected}" -gt 0 ]; then
        printf '\n    Known to fail, documented rather than broken:\n'
        local expected_failure
        for expected_failure in "${EXPECTED_FAILURES[@]}"; do
            printf '      %s\n' "${expected_failure}"
        done
    fi
    printf '\n    The container is still running. Look around with:\n'
    printf '      docker exec -it %s bash\n' "${CONTAINER_NAME}"
    printf '    Remove it with:\n'
    printf '      docker rm -f %s\n\n' "${CONTAINER_NAME}"
    [ "${failed}" -eq 0 ]
}

main() {
    parse_options "$@"
    set_up_format

    command -v docker >/dev/null || die "docker is not on PATH."
    WORK_DIR="$(mktemp -d)"
    trap 'rm -rf "${WORK_DIR}"' EXIT

    CURRENT_STEP="step 1"
    step "Step 1: build the agent package of this working tree"
    build_package

    CURRENT_STEP="step 2"
    if [ -n "${RELEASED_PACKAGE_PATH}" ]; then
        step "Step 2: take the released package from ${RELEASED_PACKAGE_PATH}"
    else
        step "Step 2: fetch the released package from ${AGENTS_URL}"
    fi
    download_package

    CURRENT_STEP="step 3"
    step "Step 3: start the container ${CONTAINER_NAME}"
    build_image
    start_container
    # Everything from here to the first installation is setup, not subject
    # under test. A failure means the run says nothing, so it ends the script
    # instead of turning into a wall of misleading check failures.
    in_container mkdir -p /packages || die "Could not create /packages in the container."
    docker cp "${WORK_DIR}/${BUILT_DEB}" "${CONTAINER_NAME}:/packages/" >/dev/null ||
        die "Could not copy ${BUILT_DEB} into the container."
    docker cp "${WORK_DIR}/${RELEASED_DEB}" "${CONTAINER_NAME}:/packages/" >/dev/null ||
        die "Could not copy ${RELEASED_DEB} into the container."
    # Refresh the package index here rather than letting the first installation
    # do it, so that a repository problem is a failure of the setup and not a
    # failure attributed to the package under test.
    if [ "${PACKAGE_FORMAT}" = "deb" ]; then
        in_container apt-get -o DPkg::Lock::Timeout=120 update >/dev/null 2>&1 ||
            die "apt-get update failed in the container."
    else
        in_container dnf makecache >/dev/null 2>&1 ||
            die "dnf makecache failed in the container."
    fi
    # shellcheck disable=SC2016  # PRETTY_NAME is expanded by the container's shell
    info "running $(in_container sh -c '. /etc/os-release && echo "${PRETTY_NAME}"')"

    # Take the versions from the packages themselves, so the checks compare
    # against what is really there rather than a prefix that ages.
    BUILT_VERSION="$(package_manager_file_version "${BUILT_DEB}" | tr -d '\n')"
    RELEASED_VERSION="$(package_manager_file_version "${RELEASED_DEB}" | tr -d '\n')"
    [ -n "${BUILT_VERSION}" ] || die "Could not read the version of ${BUILT_DEB}."
    [ -n "${RELEASED_VERSION}" ] || die "Could not read the version of ${RELEASED_DEB}."
    # The whole point is the step across the layout switch, so a site serving
    # anything but the old branch makes the run meaningless.
    # A prefix, not a dotted prefix: a daily build is 2.5.0-2026.10.30-1 and a
    # patch release is 2.5.0p18-1, so what follows the branch is not a dot.
    case "${RELEASED_VERSION}" in
        "${RELEASED_BRANCH}"*) ;;
        *) die "${AGENTS_URL} serves ${RELEASED_VERSION}, expected ${RELEASED_BRANCH}*" ;;
    esac
    info "built package:    ${BUILT_DEB} (${BUILT_VERSION})"
    info "released package: ${RELEASED_DEB} (${RELEASED_VERSION})"

    CURRENT_STEP="step 4"
    step "Step 4: install the built package on a host that never had an agent"
    install_package "${BUILT_DEB}"
    check_installation single-dir "${BUILT_VERSION}"

    CURRENT_STEP="step 6.1"
    step "Step 6.1: remove the built package"
    remove_package
    check_path absent /usr/bin/check_mk_agent

    CURRENT_STEP="step 6.2"
    step "Step 6.2: install the released 2.5 package"
    install_package "${RELEASED_DEB}"
    check_installation classic "${RELEASED_VERSION}"

    CURRENT_STEP="step 6.3"
    step "Step 6.3: customise the 2.5 installation the way a host without a bakery does"
    seed_user_files
    check_user_files_are_used
    seed_runtime_state
    check_agent_user_home "${LEGACY_HOMEDIR}"
    # Remembered rather than asserted: the upgrade must not give the agent user
    # a new uid, or every migrated runtime file ends up owned by a stranger.
    AGENT_UID_BEFORE_UPGRADE="$(in_container id -u cmk-agent | tr -d '\n')"
    info "cmk-agent has uid ${AGENT_UID_BEFORE_UPGRADE} before the upgrade"

    CURRENT_STEP="step 7"
    step "Step 7: upgrade the 2.5 installation to the built package"
    install_package "${BUILT_DEB}"
    check_installation single-dir "${BUILT_VERSION}"

    CURRENT_STEP="step 7 (migrated state)"
    info "checking what migrate.sh carried into the new tree"
    check_runtime_state_migrated
    check_agent_user_id "${AGENT_UID_BEFORE_UPGRADE}"

    CURRENT_STEP="step 7 (host's own files)"
    info "checking what became of the plug-in, the local check and the configuration"
    # AC 2 of the ticket asks for the runtime files and the controller
    # registration to move, "as migrate.sh does for baked packages", and the
    # baked packages leave the host's own files alone. So this is the behaviour
    # as specified, and the checks record what it costs the host rather than
    # claiming a defect.
    expect_failure "the ticket does not ask for the host's own files to be moved"
    check_user_files_moved
    check_user_files_are_used
    expect_failure_end

    summarize
}

main "$@"
