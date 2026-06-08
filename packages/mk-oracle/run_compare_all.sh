#!/bin/bash
# Compare outputs of the old (mk_oracle) and new (mk-oracle) plugins.
# Usage: ./run_compare_all.sh [--diff] [--keep] [--time-only]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Building release binary ==="
TARGET_DIR=$(cargo metadata --manifest-path "${SCRIPT_DIR}/Cargo.toml" --no-deps --format-version 1 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['target_directory'])")
export RELEASE_BIN="${TARGET_DIR}/release/mk-oracle"
if ! cargo build --release --manifest-path "${SCRIPT_DIR}/Cargo.toml" 2>&1; then
    echo "ERROR: release build failed" >&2
    exit 1
fi
strip "${RELEASE_BIN}"

sections=(
    jobs
    asm_instance
    sessions
    logswitches
    undostat
    recovery_area
    processes
    recovery_status
    longactivesessions
    dataguard_stats
    performance
    systemparameter
    locks
    tablespaces
    rman
    resumable
    iostats
    asm_diskgroup
    ts_quotas
)

failed_sections=()

for section in "${sections[@]}"; do
    echo "Running section: $section"
    if ! DB_SECTION="$section" "${SCRIPT_DIR}/run_comparison.sh" "$@"; then
        failed_sections+=("$section")
    fi
done

if ((${#failed_sections[@]})); then
    printf 'Different sections (%d):\n' "${#failed_sections[@]}"
    printf '  %s\n' "${failed_sections[@]}"
    exit 1
fi
