# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Old-vs-new Oracle plugin output comparison against a Dockerised database.

Runs the old bash ``mk_oracle`` and the new Rust ``mk-oracle`` against the same
containerised Oracle instance (the session-scoped ``oracle`` fixture) and asserts
their agent-section output is equivalent, apart from the deviations recorded in
``KNOWN_DEVIATIONS``.

Using the in-test Docker database (rather than a shared remote DB) keeps the
comparison self-contained and reproducible: a fresh database each run removes the
volatility and reachability problems of a shared instance. See ``comparison.py``
for exactly what is compared (section set, per-section row-key set, and per-key
column count; field values beyond the key and row order are ignored).
"""

from tests.agent_plugin_integration.comparison import ComparisonResult, PluginOutput
from tests.agent_plugin_integration.conftest import OracleDatabase

# Accepted old-vs-new differences (section names carry their ``:sep(124)`` modifier
# because that is the full header the comparison keys on). Captured against Oracle
# 23ai Free (SID FREE) with the restricted ``c##checkmk`` test user. Each entry has
# a rationale; anything not listed is treated as a regression and fails the test.
KNOWN_DEVIATIONS: dict[str, set[str]] = {
    "only_in_old": set(),
    "only_in_new": {
        # The new plugin emits an oracle_ts_quotas section (bare header + :sep(124)
        # data variant); the old bash plugin does not produce it under the default
        # section set. New-plugin addition.
        "oracle_ts_quotas",
        "oracle_ts_quotas:sep(124)",
    },
    "different": {
        # oracle_performance: two independent, accepted differences —
        #  * the OLD plugin emits a noise/debug row for the PDB
        #    ("FREE| Debug: parse: FREEPDB1: ORA-01031: insufficient privileges")
        #    because the restricted c##checkmk test user cannot read FREEPDB1's perf
        #    views; the new plugin does not emit that line;
        #  * the NEW plugin attributes PGA_info per container (FREE.FREEPDB1|PGA_info|*)
        #    whereas the old plugin does not — the more correct behaviour.
        "oracle_performance:sep(124)",
        # oracle_processes: only the current process count differs (e.g. 81 vs 82).
        # The comparison key includes that count, which is volatile between the two
        # sequential plugin runs.
        "oracle_processes:sep(124)",
        # oracle_sessions: current session counts are volatile (e.g. CDB$ROOT|4 vs 5)
        # and the aggregate FREE row count differs (71 vs 1) — a counting-scope
        # difference. Per-container rows otherwise match.
        "oracle_sessions:sep(124)",
    },
}


def _run_old_plugin(oracle: OracleDatabase) -> str:
    """Run the old bash mk_oracle in the container and return its stdout."""
    rc, output = oracle.container.exec_run(
        f"""bash -c '{oracle.cmk_plugin.as_posix()}'""", user="root"
    )
    assert isinstance(output, bytes)  # stream/socket/demux not used above
    text = output.decode("utf-8")
    assert rc == 0, f"old mk_oracle plugin failed!\n{text}"
    return text


def _run_new_plugin(oracle: OracleDatabase) -> str:
    """Run the new mk-oracle binary in the container and return its stdout."""
    rc, output = oracle.container.exec_run(
        [oracle.new_plugin.as_posix(), "-c", oracle.new_plugin_cfg.as_posix(), "--no-spool"]
    )
    assert isinstance(output, bytes)  # stream/socket/demux not used above
    text = output.decode("utf-8")
    assert rc == 0, f"new mk-oracle plugin failed!\n{text}"
    return text


def test_old_vs_new_plugin_section_equivalence(oracle: OracleDatabase) -> None:
    oracle.use_credentials()
    old_output = _run_old_plugin(oracle)

    oracle.use_new_plugin_credentials()
    new_output = _run_new_plugin(oracle)

    assert PluginOutput(old_output).sections, f"old mk_oracle produced no sections:\n{old_output}"
    assert PluginOutput(new_output).sections, f"new mk-oracle produced no sections:\n{new_output}"

    # This checks for differences:
    #   * on the sections / section names
    #   * on the keys within each shared section
    comparison = ComparisonResult(PluginOutput(old_output), PluginOutput(new_output))
    # Printed output is captured by pytest and only shown on failure.
    comparison.print_summary()
    comparison.print_detailed(show_diff=True)

    unexpected_only_in_old = sorted(set(comparison.only_in_old) - KNOWN_DEVIATIONS["only_in_old"])
    unexpected_only_in_new = sorted(set(comparison.only_in_new) - KNOWN_DEVIATIONS["only_in_new"])
    unexpected_different = sorted(set(comparison.different) - KNOWN_DEVIATIONS["different"])

    assert not (unexpected_only_in_old or unexpected_only_in_new or unexpected_different), (
        "Unexpected old-vs-new differences (not in KNOWN_DEVIATIONS):\n"
        f"  only in old (mk_oracle): {unexpected_only_in_old}\n"
        f"  only in new (mk-oracle): {unexpected_only_in_new}\n"
        f"  differing content:       {unexpected_different}\n"
        "See the captured comparison output above for the section-level diff."
    )
