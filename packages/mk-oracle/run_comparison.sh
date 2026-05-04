#!/bin/bash
# Compare outputs of the old (mk_oracle) and new (mk-oracle) plugins.
# Usage:
# DB_SECTION=<section_name> ./run_comparison.sh [--diff] [--keep] [--time-only]
# default is instance
#
# Other sections:
# jobs
# asm_instance
# sessions
# logswitches
# undostat
# recovery_area
# processes
# recovery_status
# longactivesessions
# dataguard_stats
# performance
# systemparameter
# locks
# tablespaces
# rman
# resumable
# iostats
# asm_diskgroup
# ts_quotas

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMPDIR=$(mktemp -d)
if [[ " $* " != *" --keep "* ]]; then
    trap 'rm -rf "$TMPDIR"' EXIT
fi

OLD_OUT="${TMPDIR}/old_output.txt"
NEW_OUT="${TMPDIR}/new_output.txt"

TIME_ONLY=0
if [[ " $* " == *" --time-only "* ]]; then
    TIME_ONLY=1
fi

echo "=== Building release binary ==="
RELEASE_BIN="${SCRIPT_DIR}/target/release/mk-oracle"
if ! cargo build --release --manifest-path "${SCRIPT_DIR}/Cargo.toml" 2>&1; then
    echo "ERROR: release build failed" >&2
    exit 1
fi

echo "=== Running old plugin (mk_oracle) ==="
OLD_START=$(date +%s%N)
"${SCRIPT_DIR}/run_legacy.sh" | sed '/^[[:space:]]*$/d' >"$OLD_OUT" 2>/dev/null
OLD_RC=$?
OLD_END=$(date +%s%N)
OLD_MS=$(((OLD_END - OLD_START) / 1000000))

echo "=== Running new plugin (mk-oracle) ==="
NEW_START=$(date +%s%N)
"${SCRIPT_DIR}/run_unified.sh" --binary "${RELEASE_BIN}" | sed '/^[[:space:]]*$/d' >"$NEW_OUT" 2>/dev/null
NEW_RC=$?
NEW_END=$(date +%s%N)
NEW_MS=$(((NEW_END - NEW_START) / 1000000))

DIFF_MS=$((NEW_MS - OLD_MS))

echo ""
if ((TIME_ONLY)); then
    echo "=== Timing ${DB_SECTION} ==="
    echo "Old plugin (mk_oracle):  ${OLD_MS} ms"
    echo "New plugin (mk-oracle):  ${NEW_MS} ms"
    echo "Difference:              ${DIFF_MS} ms"
else
    echo "=== Summary ${DB_SECTION} ==="
    echo "Old plugin (mk_oracle):  exit code=$OLD_RC, lines=$(wc -l <"$OLD_OUT"), bytes=$(wc -c <"$OLD_OUT"), time=${OLD_MS} ms"
    echo "New plugin (mk-oracle):  exit code=$NEW_RC, lines=$(wc -l <"$NEW_OUT"), bytes=$(wc -c <"$NEW_OUT"), time=${NEW_MS} ms"
    echo ""

    if diff -q "$OLD_OUT" "$NEW_OUT" >/dev/null 2>&1; then
        echo "Outputs are identical."
        rm -rf "$TMPDIR"
    else
        echo "Outputs differ."
        if [[ " $* " == *" --diff "* ]]; then
            echo ""
            echo "=== Diff (old = mk_oracle, new = mk-oracle) ==="
            diff --suppress-common-lines -u "$OLD_OUT" "$NEW_OUT" | head -1000
        fi
        exit 1
    fi
fi
