#!/usr/bin/env bash
# Exercise "cmk-agent-ctl install-agent" without installing anything.
#
# The mode calls dpkg and rpm by name, so a stand-in on PATH takes their place,
# and DEBUG_HOME_DIR puts the controller into the classic layout, where the
# download directory is <home>/update. Nothing here needs root and nothing
# touches the package database of this machine.
#
# Usage: smoke-install-agent.sh [path to cmk-agent-ctl]

set -u -o pipefail

# Colors only on a terminal, so that piping the output into grep stays clean.
if [ -t 1 ]; then
    readonly GREEN=$'\033[0;32m'
    readonly RED=$'\033[0;31m'
    readonly RESET=$'\033[0m'
else
    readonly GREEN=""
    readonly RED=""
    readonly RESET=""
fi

# A binary passed as the first argument wins, which is how the Bazel target
# hands over the one it built. Without it, the checkout is located from this
# script rather than from a fixed path, so any worktree works.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly HERE
REPO="${REPO:-$(git -C "${HERE}" rev-parse --show-toplevel 2>/dev/null)}"
readonly REPO
readonly CONTROLLER="${1:-${REPO}/bazel-bin/packages/cmk-agent-ctl/cmk-agent-ctl}"
readonly HASH="0123456789abcdef"

if [ ! -x "${CONTROLLER}" ]; then
    echo "No controller binary at '${CONTROLLER}'."
    echo "Build it with 'bazel build //packages/cmk-agent-ctl:cmk-agent-ctl',"
    echo "or name one: ${0##*/} <path to cmk-agent-ctl>"
    exit 2
fi

# Under Bazel the work goes below TEST_TMPDIR, which the runner cleans up even
# when the test is killed before the trap runs.
WORK="$(mktemp -d -p "${TEST_TMPDIR:-${TMPDIR:-/tmp}}")"
readonly WORK
trap 'rm -rf "${WORK}"' EXIT

readonly HOME_DIR="${WORK}/home"
readonly UPDATE_DIR="${HOME_DIR}/update"
readonly FAKE_BIN="${WORK}/bin"
readonly OUTSIDE="${WORK}/outside"
# What the stand-in was called with. The controller names the command line at
# log level info only, and the mode runs at the default level here, so the
# invocation is taken from the stand-in itself rather than from the log.
readonly CALLS="${WORK}/calls"
mkdir -p "${UPDATE_DIR}" "${FAKE_BIN}" "${OUTSIDE}"

# One stand-in for both managers: it records its arguments and obeys
# FAKE_EXIT, so a failing installation needs no second script.
cat >"${FAKE_BIN}/dpkg" <<'STANDIN'
#!/bin/sh
echo "$(basename "$0") called with: $*" >>"${FAKE_CALLS}"
echo "stand-in $(basename "$0"): nothing was installed" >&2
exit "${FAKE_EXIT:-0}"
STANDIN
chmod +x "${FAKE_BIN}/dpkg"
cp "${FAKE_BIN}/dpkg" "${FAKE_BIN}/rpm"

failures=0

# Run the mode on one request and report whether it behaved as expected.
#
# $1 title, $2 expected exit code, $3 expected text, $4 the request on standard
# input. FAKE_EXIT is passed through. The expected text is looked for in what
# the run leaves behind: the output of the mode and the call the stand-in
# recorded.
run_case() {
    local title="$1" expected_code="$2" expected_text="$3" request="$4"
    local output code evidence

    : >"${CALLS}"
    output="$(printf '%s\n' "${request}" |
        env PATH="${FAKE_BIN}:${PATH}" DEBUG_HOME_DIR="${HOME_DIR}" \
            FAKE_EXIT="${FAKE_EXIT:-0}" FAKE_CALLS="${CALLS}" \
            "${CONTROLLER}" install-agent 2>&1)"
    code=$?
    evidence="${output}
$(cat "${CALLS}")"

    echo "=== ${title}"
    printf '%s\n' "${evidence}" | grep -v '^$' | sed 's/^/    /'
    if [ "${code}" -ne "${expected_code}" ]; then
        echo "    ${RED}FAIL: exit code ${code}, expected ${expected_code}${RESET}"
        failures=$((failures + 1))
        return
    fi
    if ! printf '%s' "${evidence}" | grep -qF -- "${expected_text}"; then
        echo "    ${RED}FAIL: nothing mentions '${expected_text}'${RESET}"
        failures=$((failures + 1))
        return
    fi
    echo "    ${GREEN}ok: exit ${code}, '${expected_text}'${RESET}"
}

# Put a package of $1 into the download directory and name it.
spool() {
    local name="$1"
    echo "not a real package" >"${UPDATE_DIR}/${name}"
    echo "${UPDATE_DIR}/${name}"
}

request_for() {
    printf '{"package": "%s", "signatures": [{"certificate": "c", "signature": "s"}]}' "$1"
}

package="$(spool "${HASH}.deb")"
run_case "a deb is handed to dpkg" 0 "dpkg called with: -i ${package}" \
    "$(request_for "${package}")"
[ -e "${package}" ] && echo "    ${RED}FAIL: the package was not removed${RESET}" &&
    failures=$((failures + 1))

package="$(spool "${HASH}.rpm")"
run_case "an rpm is handed to rpm" 0 \
    "rpm called with: -vU --oldpackage --replacepkgs ${package}" \
    "$(request_for "${package}")"
[ -e "${package}" ] && echo "    ${RED}FAIL: the package was not removed${RESET}" &&
    failures=$((failures + 1))

package="$(spool "${HASH}.deb")"
FAKE_EXIT=1 run_case "a failing package manager is reported" 1 "failed, exit status: 1" \
    "$(request_for "${package}")"
[ -e "${package}" ] && echo "    ${RED}FAIL: the package was not removed${RESET}" &&
    failures=$((failures + 1))

# A package of our own, so that the case does not depend on a system file that
# a test sandbox may not carry.
echo "not a real package" >"${OUTSIDE}/${HASH}.deb"
run_case "a package outside the download directory is refused" 1 "lies outside" \
    "$(request_for "${OUTSIDE}/${HASH}.deb")"

ln -sf "${OUTSIDE}/${HASH}.deb" "${UPDATE_DIR}/${HASH}.deb"
run_case "a link out of the download directory is refused" 1 "lies outside" \
    "$(request_for "${UPDATE_DIR}/${HASH}.deb")"
rm -f "${UPDATE_DIR}/${HASH}.deb"

package="$(spool "check-mk-agent.deb")"
run_case "a package not named after a hash is refused" 1 "not named after an agent hash" \
    "$(request_for "${package}")"
rm -f "${package}"

package="$(spool "${HASH}.tgz")"
run_case "a package of another type is refused" 1 "expected a .deb or .rpm file" \
    "$(request_for "${package}")"
rm -f "${package}"

run_case "something that is not a request is refused" 1 "Failed to parse the install request" \
    "/tmp/${HASH}.deb"

echo
if [ "${failures}" -eq 0 ]; then
    echo "${GREEN}all cases passed${RESET}"
else
    echo "${RED}${failures} case(s) failed${RESET}"
fi
exit "${failures}"
