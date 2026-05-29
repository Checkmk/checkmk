#!/usr/bin/env bash
# Check and install prerequisites for the mk-oracle performance benchmark.
#
# What this script does:
#   1. Verifies required tools are present (Docker, Java, unzip)
#   2. Creates .env from .env.docker if no .env exists yet
#   3. Pre-fetches the mk-oracle binary via Bazel so the first benchmark run
#      does not pay the build cost
#
# Everything else (Oracle Instant Client, mk-oracle binary path, sqlplus) is
# resolved automatically by measure.py at runtime via Bazel.
#
# Usage: ./install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

ok() { echo "  [ok]  $*"; }
warn() { echo "  [!!]  $*"; }
fail() {
    echo "  [XX]  $*" >&2
    FAILED=1
}

FAILED=0

echo ""
echo "=== Checking prerequisites ==="
echo ""

# Docker
if docker info >/dev/null 2>&1; then
    ok "Docker is running"
else
    fail "Docker is not running — install Docker and start the daemon"
fi

# Java (required by charbench for bench-phases.py phase 3 load testing)
if java -version >/dev/null 2>&1; then
    ok "Java: $(java -version 2>&1 | head -1)"
else
    warn "Java not found — needed for bench-phases.py phase 3 (charbench load driver)"
    warn "Install with: sudo apt install default-jre"
fi

# unzip (used to extract Swingbench below)
if command -v unzip >/dev/null 2>&1; then
    ok "unzip: $(unzip -v 2>&1 | head -1)"
else
    fail "unzip not found — install with: sudo apt install unzip"
fi

# Bazel (used by measure.py to resolve mk-oracle binary and Oracle Instant Client)
if command -v bazel >/dev/null 2>&1; then
    ok "Bazel: $(bazel version 2>/dev/null | grep 'Build label' | cut -d: -f2 | xargs)"
else
    fail "bazel not found — required to build mk-oracle and resolve Oracle Instant Client"
fi

echo ""
echo "=== Setting up .env ==="
echo ""

if [[ -f "${SCRIPT_DIR}/.env" ]]; then
    ok ".env already exists — skipping (delete it to reset to Docker defaults)"
else
    cp "${SCRIPT_DIR}/.env.docker" "${SCRIPT_DIR}/.env"
    ok ".env created from .env.docker (local Docker database)"
fi

echo ""
echo "=== Swingbench ==="
echo ""

SWINGBENCH_DIR="${SCRIPT_DIR}/swingbench"
SWINGBENCH_ZIP="${SCRIPT_DIR}/swingbench.zip"
SWINGBENCH_URL="https://github.com/domgiles/swingbench-public/releases/download/production/swingbenchlatest.zip"

if [[ -d "${SWINGBENCH_DIR}" ]]; then
    ok "Swingbench already extracted at ${SWINGBENCH_DIR}"
else
    if [[ ! -f "${SWINGBENCH_ZIP}" ]]; then
        if command -v wget >/dev/null 2>&1; then
            echo "  Downloading Swingbench..."
            wget --show-progress -O "${SWINGBENCH_ZIP}" "${SWINGBENCH_URL}"
        elif command -v curl >/dev/null 2>&1; then
            echo "  Downloading Swingbench..."
            curl -L --progress-bar -o "${SWINGBENCH_ZIP}" "${SWINGBENCH_URL}"
        else
            fail "wget or curl required to download Swingbench — install one and rerun"
        fi
    else
        ok "Using existing ${SWINGBENCH_ZIP}"
    fi

    if [[ -f "${SWINGBENCH_ZIP}" ]]; then
        echo "  Extracting..."
        unzip -q "${SWINGBENCH_ZIP}" -d "${SCRIPT_DIR}"
        # Handle unexpected extracted directory name
        if [[ ! -d "${SWINGBENCH_DIR}" ]]; then
            extracted=$(find "${SCRIPT_DIR}" -maxdepth 1 -type d -name 'swingbench*' ! -path "${SWINGBENCH_DIR}" | head -1)
            [[ -n "${extracted}" ]] && mv "${extracted}" "${SWINGBENCH_DIR}"
        fi
        ok "Swingbench extracted to ${SWINGBENCH_DIR}"
    fi
fi

echo ""
echo "=== Pre-building mk-oracle ==="
echo ""

if ((FAILED)); then
    warn "Skipping build — fix the errors above first"
else
    echo "  Building //packages/mk-oracle:mk-oracle -c opt ..."
    bazel build //packages/mk-oracle:mk-oracle -c opt \
        --ui_event_filters=-INFO,-DEBUG,-WARNING 2>&1 | tail -3
    BAZEL_BIN="$(bazel info -c opt bazel-bin 2>/dev/null)"
    MK_ORACLE_BIN="${BAZEL_BIN}/packages/mk-oracle/mk-oracle"
    ok "mk-oracle binary: ${MK_ORACLE_BIN}"

    OCI_LIB_DIR=""
    for candidate in "${HOME}"/.cache/bazel/*/*/external/*/instantclient_*; do
        if [[ -f "${candidate}/libclntsh.so" ]]; then
            OCI_LIB_DIR="${candidate}"
            break
        fi
    done
    [[ -n "${OCI_LIB_DIR}" ]] && ok "OCI lib dir:   ${OCI_LIB_DIR}" ||
        warn "libclntsh.so not found — set OCI_LIB_DIR manually if connections fail"

    if [[ -n "${OCI_LIB_DIR}" && -f "${OCI_LIB_DIR}/sqlplus" ]]; then
        mkdir -p "${OCI_LIB_DIR}/bin"
        cp -n "${OCI_LIB_DIR}/sqlplus" "${OCI_LIB_DIR}/bin/sqlplus"
        ok "sqlplus copied to ${OCI_LIB_DIR}/bin/"
    fi

    ENV_FILE="${SCRIPT_DIR}/.env"
    grep -v "^export MK_ORACLE_BIN=\|^export OCI_LIB_DIR=" "${ENV_FILE}" >"${ENV_FILE}.tmp" &&
        mv "${ENV_FILE}.tmp" "${ENV_FILE}"
    echo "export MK_ORACLE_BIN=${MK_ORACLE_BIN}" >>"${ENV_FILE}"
    [[ -n "${OCI_LIB_DIR}" ]] && echo "export OCI_LIB_DIR=${OCI_LIB_DIR}" >>"${ENV_FILE}"
    ok ".env updated with binary paths"
fi

echo ""
if ((FAILED)); then
    echo "Prerequisites check FAILED — address the errors above before running benchmarks."
    exit 1
else
    echo "All prerequisites satisfied."
    echo ""
    echo "Next steps:"
    echo "  ./setup.py up            # start the Docker Oracle container"
    echo "  ./measure.py             # run a quick benchmark (standard scenario, 3 runs)"
    echo "  ./bench-phases.py        # full three-phase benchmark"
fi
echo ""
