#!/bin/bash
# Compare outputs of the old (mk_oracle) and new (mk-oracle) plugins.
# Usage:
# DB_SECTION=<section_name> ./run_comparison.sh
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
# jobs
# resumable
# iostats
# asm_diskgroup
# ts_quotas

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMPDIR=$(mktemp -d)
# trap 'rm -rf "$TMPDIR"' EXIT

OLD_OUT="${TMPDIR}/old_output.txt"
NEW_OUT="${TMPDIR}/new_output.txt"

echo "=== Running old plugin (mk_oracle) ==="
"${SCRIPT_DIR}/run_legacy.sh" | sed '/^[[:space:]]*$/d' >"$OLD_OUT" 2>/dev/null
OLD_RC=$?

echo "=== Running new plugin (mk-oracle) ==="
"${SCRIPT_DIR}/run_unified.sh" | sed '/^[[:space:]]*$/d' >"$NEW_OUT" 2>/dev/null
NEW_RC=$?

echo ""
echo "=== Summary ==="
echo "Old plugin (mk_oracle):  exit code=$OLD_RC, lines=$(wc -l <"$OLD_OUT"), bytes=$(wc -c <"$OLD_OUT")"
echo "New plugin (mk-oracle):  exit code=$NEW_RC, lines=$(wc -l <"$NEW_OUT"), bytes=$(wc -c <"$NEW_OUT")"
echo ""

if diff -q "$OLD_OUT" "$NEW_OUT" >/dev/null 2>&1; then
    echo "Outputs are identical."
else
    echo "Outputs differ."
    if [[ " $* " == *" --diff "* ]]; then
        echo ""
        echo "=== Diff (old = mk_oracle, new = mk-oracle) ==="
        diff --suppress-common-lines -u "$OLD_OUT" "$NEW_OUT" | head -500
    fi
fi
