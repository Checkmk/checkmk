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

# One stand-in for both managers: it records its arguments and the content it
# was handed, and obeys FAKE_EXIT, so a failing installation needs no second
# script. The content matters because the mode hands over a descriptor of the
# bytes it verified, not the directory entry.
cat >"${FAKE_BIN}/dpkg" <<'STANDIN'
#!/bin/sh
for argument in "$@"; do package="${argument}"; done
{
    echo "$(basename "$0") called with: $*"
    echo "$(basename "$0") read: $(head -c 64 "${package}")"
} >>"${FAKE_CALLS}"
echo "stand-in $(basename "$0"): nothing was installed" >&2
exit "${FAKE_EXIT:-0}"
STANDIN
chmod +x "${FAKE_BIN}/dpkg"
cp "${FAKE_BIN}/dpkg" "${FAKE_BIN}/rpm"

if ! command -v openssl >/dev/null; then
    echo "openssl is needed to sign the test packages."
    exit 2
fi

# The trust anchor of this run: an RSA certificate in an update configuration,
# as the bakery writes it, plus the key to sign packages with.
readonly KEY="${WORK}/key.pem"
readonly CERTIFICATE="${WORK}/cert.pem"
readonly CONFIG="${WORK}/cmk-agent-ctl-update.toml"
openssl req -x509 -newkey rsa:2048 -nodes -days 2 -subj "/CN=smoke-install-agent" \
    -keyout "${KEY}" -out "${CERTIFICATE}" 2>/dev/null
{
    echo 'activated = true'
    echo 'signature_keys = ["""'
    cat "${CERTIFICATE}"
    echo '"""]'
} >"${CONFIG}"

failures=0

# Run the mode on one request and report whether it behaved as expected.
#
# $1 title, $2 expected exit code, $3 expected text, $4 the request on standard
# input. FAKE_EXIT and CONFIG_PATH are passed through, so that a case can let
# the package manager fail or name another update configuration. The expected
# text is looked for in what the run leaves behind: the output of the mode and
# what the stand-in recorded.
run_case() {
    local title="$1" expected_code="$2" expected_text="$3" request="$4"
    local output code evidence

    : >"${CALLS}"
    output="$(printf '%s\n' "${request}" |
        env PATH="${FAKE_BIN}:${PATH}" DEBUG_HOME_DIR="${HOME_DIR}" \
            CMK_AGENT_CTL_UPDATE_CONFIG="${CONFIG_PATH:-${CONFIG}}" \
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

# The certificate as one JSON string, newlines escaped as the site sends them.
json_certificate() {
    awk 'BEGIN { printf "\"" } { printf "%s\\n", $0 } END { printf "\"" }' "${CERTIFICATE}"
}

# A request for $1, signed with the key of the trust anchor. SIGN_INSTEAD names
# a file to sign in its place, which is how a package nothing vouches for is
# built.
request_for() {
    local package="$1" signature
    signature="$(openssl dgst -sha256 -sign "${KEY}" "${SIGN_INSTEAD:-${package}}" |
        openssl base64 -A)"
    printf '{"package": "%s", "signatures": [{"certificate": %s, "signature": "%s"}]}' \
        "${package}" "$(json_certificate)" "${signature}"
}

# A request for $1 that carries no signature at all.
unsigned_request_for() {
    printf '{"package": "%s", "signatures": []}' "$1"
}

# The package manager is handed /proc/<pid>/fd/<n> of the verified bytes, not
# the directory entry, which is why these cases match on "/proc/" and one of
# them on the content that arrived there.
package="$(spool "${HASH}.deb")"
run_case "a deb is handed to dpkg" 0 "dpkg called with: -i /proc/" \
    "$(request_for "${package}")"
[ -e "${package}" ] && echo "    ${RED}FAIL: the package was not removed${RESET}" &&
    failures=$((failures + 1))

package="$(spool "${HASH}.deb")"
run_case "the verified bytes reach the package manager" 0 "dpkg read: not a real package" \
    "$(request_for "${package}")"

package="$(spool "${HASH}.rpm")"
run_case "an rpm is handed to rpm" 0 \
    "rpm called with: -vU --oldpackage --replacepkgs /proc/" \
    "$(request_for "${package}")"
[ -e "${package}" ] && echo "    ${RED}FAIL: the package was not removed${RESET}" &&
    failures=$((failures + 1))

package="$(spool "${HASH}.deb")"
FAKE_EXIT=1 run_case "a failing package manager is reported" 1 "failed, exit status: 1" \
    "$(request_for "${package}")"
[ -e "${package}" ] && echo "    ${RED}FAIL: the package was not removed${RESET}" &&
    failures=$((failures + 1))

package="$(spool "${HASH}.deb")"
echo "another package" >"${OUTSIDE}/other.deb"
# Set before the request is built: a prefix on run_case would come too late,
# the argument is expanded first.
SIGN_INSTEAD="${OUTSIDE}/other.deb"
mismatched_request="$(request_for "${package}")"
unset SIGN_INSTEAD
run_case "a package the signature does not cover is refused" 1 \
    "no signature of it matches a configured signature key" "${mismatched_request}"
rm -f "${package}"

package="$(spool "${HASH}.deb")"
run_case "an unsigned package is refused" 1 "no signature of it matches a configured signature key" \
    "$(unsigned_request_for "${package}")"
rm -f "${package}"

package="$(spool "${HASH}.deb")"
CONFIG_PATH="${WORK}/absent.toml" run_case "a missing update configuration is refused" 1 \
    "No updater configuration" "$(request_for "${package}")"
rm -f "${package}"

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
