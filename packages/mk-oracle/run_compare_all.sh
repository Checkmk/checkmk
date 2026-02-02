#!/bin/bash
# Compare outputs of the old (mk_oracle) and new (mk-oracle) plugins.

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
    if ! DB_SECTION="$section" ./run_comparison.sh "$*"; then
        failed_sections+=("$section")
    fi
done

if ((${#failed_sections[@]})); then
    printf 'Different sections (%d):\n' "${#failed_sections[@]}"
    printf '  %s\n' "${failed_sections[@]}"
    exit 1
fi
