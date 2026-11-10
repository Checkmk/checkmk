#!/usr/bin/env bash
# Exercise "cmk-agent-ctl install-agent" without installing anything.
#
# The mode calls dpkg and rpm by name, so a stand-in on PATH takes their place,
# and DEBUG_HOME_DIR puts the controller into the classic layout, where the
# install result goes to <home>. Nothing here needs root and nothing touches
# the package database of this machine.
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
readonly FAKE_BIN="${WORK}/bin"
# What the stand-in was called with. The controller names the command line at
# log level info only, and the mode runs at the default level here, so the
# invocation is taken from the stand-in itself rather than from the log.
readonly CALLS="${WORK}/calls"
mkdir -p "${HOME_DIR}" "${FAKE_BIN}"

# One stand-in for both managers: it records its arguments and the content it
# was handed, and obeys FAKE_EXIT, so a failing installation needs no second
# script. The content matters because the mode hands over a descriptor of the
# bytes it verified.
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

readonly PACKAGE="${WORK}/package"
echo "not a real package" >"${PACKAGE}"
readonly OTHER_PACKAGE="${WORK}/other-package"
echo "another package" >"${OTHER_PACKAGE}"

failures=0

# Run the mode on one conversation and report whether it behaved as expected.
#
# $1 title, $2 expected exit code, $3 expected text, $4 the file that holds
# what the controller sends. FAKE_EXIT and CONFIG_PATH are passed through, so
# that a case can let the package manager fail or name another update
# configuration. The expected text is looked for in what the run leaves
# behind: what the mode logged and answered, and what the stand-in recorded.
run_case() {
    local title="$1" expected_code="$2" expected_text="$3" input="$4"
    local output code evidence

    : >"${CALLS}"
    output="$(env PATH="${FAKE_BIN}:${PATH}" DEBUG_HOME_DIR="${HOME_DIR}" \
        CMK_AGENT_CTL_UPDATE_CONFIG="${CONFIG_PATH:-${CONFIG}}" \
        FAKE_EXIT="${FAKE_EXIT:-0}" FAKE_CALLS="${CALLS}" \
        "${CONTROLLER}" install-agent <"${input}" 2>&1)"
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

# The certificate as one JSON string, newlines escaped as the site sends them.
json_certificate() {
    awk 'BEGIN { printf "\"" } { printf "%s\\n", $0 } END { printf "\"" }' "${CERTIFICATE}"
}

# Write what the controller sends for the package $1 of the platform $2, and
# name the file: the request, signed with the key of the trust anchor, the
# package bytes and the install line. The line goes along right away, because
# the mode reads it only after it has accepted the package.
#
# SIGN_INSTEAD names a file to sign in place of the package, which is how a
# package nothing vouches for is built. UNSIGNED leaves the signatures out,
# SIZE announces another length, and NO_INSTALL leaves out the install line.
conversation() {
    local package="$1" platform="$2" input="${WORK}/input" signatures size
    if [ -n "${UNSIGNED:-}" ]; then
        signatures="[]"
    else
        signatures="[{\"certificate\": $(json_certificate), \"signature\": \"$(
            openssl dgst -sha256 -sign "${KEY}" "${SIGN_INSTEAD:-${package}}" | openssl base64 -A
        )\"}]"
    fi
    size="${SIZE:-$(wc -c <"${package}" | tr -d ' ')}"
    {
        printf '{"aghash": "%s", "platform": "%s", "size": %s, "signatures": %s}\n' \
            "${HASH}" "${platform}" "${size}" "${signatures}"
        cat "${package}"
        [ -n "${NO_INSTALL:-}" ] || echo install
    } >"${input}"
    echo "${input}"
}

# The package manager is handed /proc/<pid>/fd/<n> of the verified bytes,
# which is why these cases match on "/proc/" and one of them on the content
# that arrived there.
run_case "a deb is handed to dpkg" 0 "dpkg called with: -i /proc/" \
    "$(conversation "${PACKAGE}" linux_deb)"

run_case "the verified bytes reach the package manager" 0 "dpkg read: not a real package" \
    "$(conversation "${PACKAGE}" linux_deb)"

run_case "an rpm is handed to rpm" 0 \
    "rpm called with: -vU --oldpackage --replacepkgs /proc/" \
    "$(conversation "${PACKAGE}" linux_rpm)"

run_case "the result goes back to the controller" 0 '"success":true' \
    "$(conversation "${PACKAGE}" linux_deb)"

FAKE_EXIT=1 run_case "a failing package manager is reported" 1 "failed, exit status: 1" \
    "$(conversation "${PACKAGE}" linux_deb)"

run_case "a package the signature does not cover is refused" 1 \
    "No signature of the package matches a configured signature key" \
    "$(SIGN_INSTEAD="${OTHER_PACKAGE}" conversation "${PACKAGE}" linux_deb)"

run_case "an unsigned package is refused" 1 '"accepted":false' \
    "$(UNSIGNED=1 conversation "${PACKAGE}" linux_deb)"

CONFIG_PATH="${WORK}/absent.toml" run_case "a missing update configuration is refused" 1 \
    "No updater configuration" "$(conversation "${PACKAGE}" linux_deb)"

run_case "a platform without a package manager is refused" 1 \
    "No package manager installs packages of the platform" \
    "$(conversation "${PACKAGE}" windows_msi)"

run_case "a transfer shorter than its size is refused" 1 "ended the transfer after" \
    "$(SIZE=1000 conversation "${PACKAGE}" linux_deb)"

run_case "without the install line nothing is installed" 1 "before it asked to install" \
    "$(NO_INSTALL=1 conversation "${PACKAGE}" linux_deb)"
grep -q "called with" "${CALLS}" &&
    echo "    ${RED}FAIL: the package manager ran${RESET}" &&
    failures=$((failures + 1))

echo "/tmp/${HASH}.deb" >"${WORK}/not-a-request"
run_case "something that is not a request is refused" 1 "Failed to parse the install request" \
    "${WORK}/not-a-request"

echo
if [ "${failures}" -eq 0 ]; then
    echo "${GREEN}all cases passed${RESET}"
else
    echo "${RED}${failures} case(s) failed${RESET}"
fi
exit "${failures}"
