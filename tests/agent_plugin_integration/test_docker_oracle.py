#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from pathlib import Path
from typing import Final, Literal

import pytest

from tests.agent_plugin_integration.comparison import ComparisonResult, PluginOutput
from tests.agent_plugin_integration.conftest import OracleDatabase
from tests.agent_plugin_integration.test_plugin_comparison import (
    KNOWN_DEVIATIONS,
    run_old_plugin,
)
from tests.testlib.docker import copy_to_container

_SECTION_HEADER_RE = re.compile(r"^<<<([^>:]+)")

# Expected number of pipe-separated columns per performance category.
_PERF_CATEGORY_COLUMNS: Final[dict[str, int]] = {
    "PGA_info": 5,
    "SGA_info": 4,
    "librarycache": 9,
    "sys_time_model": 4,
    "sys_wait_class": 7,
    "buffer_pool_statistics": 10,
    "iostat_file": 15,
}


def _parse_oracle_sections(
    output: str,
) -> tuple[list[str], list[str], list[str]]:
    """Parse mk-oracle agent output and classify sections by their data content.

    Section headers may carry optional modifiers that are stripped when extracting
    the section name:
        <<<name>>>
        <<<name:sep(124)>>>
        <<<name:cached(ts,age):sep(124)>>>

    A section name can appear multiple times in the output (e.g. ``oracle_instance``
    is emitted once per database instance).  Classification is based on the union of
    all occurrences:

    - ``all_sections``       – unique names that appear at least once
    - ``empty_sections``     – names whose *every* occurrence produced no data lines
    - ``error_sections``     – names where at least one occurrence contains a line
                               with ``FAILURE`` or ``ERROR:``
    - ``non_empty_sections`` – names where at least one occurrence produced data
                               lines that contain neither ``FAILURE`` nor ``ERROR:``
    """
    chunks: list[tuple[str, list[str]]] = []
    current_name: str | None = None
    current_data: list[str] = []

    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("<<<") and stripped.endswith(">>>"):
            m = _SECTION_HEADER_RE.match(stripped)
            if m:
                if current_name is not None:
                    chunks.append((current_name, current_data))
                current_name = m.group(1)
                current_data = []
                continue
        if current_name is not None and stripped:
            current_data.append(stripped)

    if current_name is not None:
        chunks.append((current_name, current_data))

    has_non_error_data: set[str] = set()
    has_error_data: set[str] = set()
    has_empty: set[str] = set()
    seen: dict[str, None] = {}  # insertion-ordered unique names

    for name, data in chunks:
        seen[name] = None
        if not data:
            has_empty.add(name)
        elif any("FAILURE" in ln or "ERROR:" in ln for ln in data):
            has_error_data.add(name)
        else:
            has_non_error_data.add(name)

    all_sections = list(seen)
    error_sections = [n for n in all_sections if n in has_error_data]
    non_empty_sections = [n for n in all_sections if n in has_non_error_data]

    return all_sections, error_sections, non_empty_sections


def _parse_section_chunks(output: str) -> dict[str, list[str]]:
    """Parse mk-oracle output into a mapping from section name to data lines.

    A section may appear multiple times (e.g. ``oracle_instance`` once per
    database instance).  All data lines across every occurrence are collected
    under the section's name.  Section header lines (``<<<name>>>`` and
    ``<<<name:sep(124)>>>``) are excluded from the returned data.
    """
    chunks: dict[str, list[str]] = {}
    current_name: str | None = None
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("<<<") and stripped.endswith(">>>"):
            m = _SECTION_HEADER_RE.match(stripped)
            if m:
                current_name = m.group(1)
                chunks.setdefault(current_name, [])
                continue
        if current_name is not None and stripped:
            chunks[current_name].append(stripped)
    return chunks


def _run_new_plugin(oracle: OracleDatabase, config_path: Path | None = None) -> str:
    """Run the mk-oracle binary inside the container and return its stdout."""
    cfg = (config_path or oracle.new_plugin_cfg).as_posix()
    rc, output = oracle.container.exec_run([oracle.new_plugin.as_posix(), "-c", cfg, "--no-spool"])
    assert isinstance(output, bytes)  # stream/socket/demux not used above
    text = output.decode("utf-8")
    assert rc == 0, f"mk-oracle plugin failed!\n{text}"
    return text


def _run_new_plugin_as_root(oracle: OracleDatabase, config_path: Path | None = None) -> str:
    """Run the mk-oracle binary inside the container as root and return its output.

    Unlike `_run_new_plugin`, success is not asserted: run as root against a
    non-root-owned runtime the plugin refuses to load and exits non-zero, so
    callers assert on the output instead of the exit code. `exec_run` merges
    stderr into stdout, so the refusal message is part of the return value.
    """
    cfg = (config_path or oracle.new_plugin_cfg).as_posix()
    _, output = oracle.container.exec_run(
        [oracle.new_plugin.as_posix(), "-c", cfg, "--no-spool"], user="root"
    )
    assert isinstance(output, bytes)  # stream/socket/demux not used above
    return output.decode("utf-8")


def _install_custom_config(oracle: OracleDatabase, content: str, name: str) -> Path:
    """Write the YAML to the temp dir, copy into the container and return its container path."""
    host_path = oracle.ORAENV / name
    host_path.write_text(content, encoding="UTF-8")
    assert copy_to_container(oracle.container, host_path, oracle.cmk_cfg_dir), (
        f'Failed to copy "{name}" to container'
    )
    return oracle.cmk_cfg_dir / name


@pytest.fixture(name="mk_oracle_sections", scope="session")
def _mk_oracle_sections(oracle: OracleDatabase) -> dict[str, list[str]]:
    """Run mk-oracle once with credential auth and cache the parsed sections."""
    oracle.use_new_plugin_credentials()
    output = _run_new_plugin(oracle)
    return _parse_section_chunks(output)


def _assert_rows_start_with_sid(rows: list[str], sid: str) -> None:
    """Assert each row's first pipe-separated field starts with ``sid``."""
    for row in rows:
        first = row.split("|", 1)[0]
        assert first.startswith(sid), f"Row does not start with SID={sid!r}: {row}"


def test_mk_oracle_section_instance(
    oracle: OracleDatabase, mk_oracle_sections: dict[str, list[str]]
) -> None:
    rows = mk_oracle_sections.get("oracle_instance", [])
    assert len(rows) >= 2, f"Expected at least 2 instance rows: {rows}"
    _assert_rows_start_with_sid(rows, oracle.SID)


def test_mk_oracle_section_sessions(
    oracle: OracleDatabase, mk_oracle_sections: dict[str, list[str]]
) -> None:
    rows = mk_oracle_sections.get("oracle_sessions", [])
    assert rows, "oracle_sessions is empty"
    _assert_rows_start_with_sid(rows, oracle.SID)


def test_mk_oracle_section_logswitches(
    oracle: OracleDatabase, mk_oracle_sections: dict[str, list[str]]
) -> None:
    rows = mk_oracle_sections.get("oracle_logswitches", [])
    assert rows, "oracle_logswitches is empty"
    _assert_rows_start_with_sid(rows, oracle.SID)


def test_mk_oracle_section_undostat(
    oracle: OracleDatabase, mk_oracle_sections: dict[str, list[str]]
) -> None:
    rows = mk_oracle_sections.get("oracle_undostat", [])
    assert rows, "oracle_undostat is empty"
    _assert_rows_start_with_sid(rows, oracle.SID)


def test_mk_oracle_section_processes(
    oracle: OracleDatabase, mk_oracle_sections: dict[str, list[str]]
) -> None:
    rows = mk_oracle_sections.get("oracle_processes", [])
    assert rows, "oracle_processes is empty"
    _assert_rows_start_with_sid(rows, oracle.SID)


def test_mk_oracle_section_recovery_status(
    oracle: OracleDatabase, mk_oracle_sections: dict[str, list[str]]
) -> None:
    rows = mk_oracle_sections.get("oracle_recovery_status", [])
    assert rows, "oracle_recovery_status is empty"
    _assert_rows_start_with_sid(rows, oracle.SID)


def test_mk_oracle_section_longactivesessions(
    oracle: OracleDatabase, mk_oracle_sections: dict[str, list[str]]
) -> None:
    rows = mk_oracle_sections.get("oracle_longactivesessions", [])
    assert rows, "oracle_longactivesessions is empty"
    cdb_marker = f"{oracle.SID}.CDB$ROOT|"
    assert any(r.startswith(cdb_marker) for r in rows), (
        f"Missing CDB$ROOT row prefixed with {cdb_marker}: {rows}"
    )
    pdb_marker = f"{oracle.SID}.{oracle.PDB}|"
    assert any(r.startswith(pdb_marker) for r in rows), (
        f"Missing PDB row prefixed with {pdb_marker}: {rows}"
    )


def test_mk_oracle_section_performance(
    oracle: OracleDatabase, mk_oracle_sections: dict[str, list[str]]
) -> None:
    rows = mk_oracle_sections.get("oracle_performance", [])
    assert rows, "oracle_performance is empty"
    _assert_rows_start_with_sid(rows, f"{oracle.SID}.")


def test_mk_oracle_section_performance_categories(
    oracle: OracleDatabase, mk_oracle_sections: dict[str, list[str]]
) -> None:
    """Each performance row must use a known category and the expected column count."""
    rows = mk_oracle_sections.get("oracle_performance", [])
    assert rows, "oracle_performance is empty"
    seen: set[str] = set()
    for row in rows:
        parts = row.split("|")
        category = parts[1]
        assert category in _PERF_CATEGORY_COLUMNS, f"Unknown performance category in row: {row}"
        assert len(parts) == _PERF_CATEGORY_COLUMNS[category], (
            f"Wrong column count for {category!r}: {row}"
        )
        seen.add(category)
    for required in ("SGA_info", "librarycache", "sys_time_model", "buffer_pool_statistics"):
        assert required in seen, f"Missing performance category {required!r}"


def test_mk_oracle_section_locks(
    oracle: OracleDatabase, mk_oracle_sections: dict[str, list[str]]
) -> None:
    rows = mk_oracle_sections.get("oracle_locks", [])
    assert rows, "oracle_locks is empty"
    _assert_rows_start_with_sid(rows, oracle.SID)


def test_mk_oracle_section_systemparameter(
    oracle: OracleDatabase, mk_oracle_sections: dict[str, list[str]]
) -> None:
    rows = mk_oracle_sections.get("oracle_systemparameter", [])
    assert rows, "oracle_systemparameter is empty"
    _assert_rows_start_with_sid(rows, oracle.SID)


def test_mk_oracle_section_ts_quotas(
    oracle: OracleDatabase, mk_oracle_sections: dict[str, list[str]]
) -> None:
    rows = mk_oracle_sections.get("oracle_ts_quotas", [])
    assert rows, "oracle_ts_quotas is empty"
    _assert_rows_start_with_sid(rows, oracle.SID)


def test_mk_oracle_section_jobs(
    oracle: OracleDatabase, mk_oracle_sections: dict[str, list[str]]
) -> None:
    rows = mk_oracle_sections.get("oracle_jobs", [])
    assert rows, "oracle_jobs is empty"
    _assert_rows_start_with_sid(rows, oracle.SID)


def test_mk_oracle_section_resumable(
    oracle: OracleDatabase, mk_oracle_sections: dict[str, list[str]]
) -> None:
    rows = mk_oracle_sections.get("oracle_resumable", [])
    assert rows, "oracle_resumable is empty"
    _assert_rows_start_with_sid(rows, oracle.SID)


def test_mk_oracle_section_tablespaces(
    oracle: OracleDatabase, mk_oracle_sections: dict[str, list[str]]
) -> None:
    rows = mk_oracle_sections.get("oracle_tablespaces", [])
    assert rows, "oracle_tablespaces is empty"
    _assert_rows_start_with_sid(rows, oracle.SID)


def _sid_only_yml(oracle: OracleDatabase) -> str:
    return "\n".join(
        [
            "---",
            "oracle:",
            "  main:",
            "    connection:",
            "      hostname: localhost",
            f"      port: {oracle.PORT}",
            "    authentication:",
            f"      username: {oracle.cmk_username}",
            f"      password: {oracle.cmk_password}",
            "      type: standard",
            "    sections:",
            "      - instance:",
            "    discovery:",
            "      detect: no",
            "    instances:",
            f"      - sid: {oracle.SID}",
        ]
    )


def _custom_instance_yml(oracle: OracleDatabase, include: str, alias: str | None = None) -> str:
    return "\n".join(
        [
            "---",
            "oracle:",
            "  main:",
            "    connection:",
            "      hostname: absent.localhost",
            "      timeout: 5",
            "    authentication:",
            f"      username: {oracle.cmk_username}",
            f"      password: {oracle.cmk_password}",
            "      type: standard",
            "    sections:",
            "      - instance:",
            "    discovery:",
            "      detect: no",
            f"      include: [{include}]",
            "      exclude: []",
            "    instances:",
            f"      - service_name: {include}",
            *([f"        alias: {alias}"] if alias else []),
            "        connection:",
            "          hostname: localhost",
            f"          port: {oracle.PORT}",
            "        authentication:",
            f"          username: {oracle.cmk_username}",
            f"          password: {oracle.cmk_password}",
            "          type: standard",
        ]
    )


def test_mk_oracle_sid_only_connection(oracle: OracleDatabase) -> None:
    cfg_path = _install_custom_config(oracle, _sid_only_yml(oracle), "mk-oracle.sid-only.yml")
    output = _run_new_plugin(oracle, cfg_path)
    chunks = _parse_section_chunks(output)
    rows = chunks.get("oracle_instance", [])
    assert rows, f"No oracle_instance rows in output:\n{output}"
    for row in rows:
        assert row.startswith(f"{oracle.SID}|"), f"Row does not start with SID: {row}"


def test_mk_oracle_run_as_root_is_refused(oracle: OracleDatabase) -> None:
    output = _run_new_plugin_as_root(oracle)
    assert "<<<" not in output, f"Expected no section output when run as root, got:\n{output}"
    assert "No Oracle client runtime found" in output, (
        f"Expected the runtime refusal when run as root, got:\n{output}"
    )


def test_mk_oracle_custom_instance_connection(oracle: OracleDatabase) -> None:
    cfg_path = _install_custom_config(
        oracle, _custom_instance_yml(oracle, oracle.SID), "mk-oracle.custom-instance.yml"
    )
    output = _run_new_plugin(oracle, cfg_path)
    chunks = _parse_section_chunks(output)
    rows = chunks.get("oracle_instance", [])
    assert rows, f"No oracle_instance rows in output:\n{output}"
    for row in rows:
        assert row.startswith(oracle.SID), f"Row does not start with SID: {row}"


def test_mk_oracle_absent_custom_instance_connection(oracle: OracleDatabase) -> None:
    cfg_path = _install_custom_config(
        oracle, _custom_instance_yml(oracle, "absent"), "mk-oracle.absent-instance.yml"
    )
    output = _run_new_plugin(oracle, cfg_path)
    chunks = _parse_section_chunks(output)
    rows = chunks.get("oracle_instance", [])
    assert rows, f"No oracle_instance rows in output:\n{output}"
    assert any("FAILURE" in r and "ERROR: ORA-" in r for r in rows), (
        f"Expected an ORA- failure row for the absent instance:\n{output}"
    )


def test_mk_oracle_wallet_authentication(oracle: OracleDatabase) -> None:
    """Verify mk-oracle can connect to the database using Oracle wallet auth."""
    oracle.use_new_plugin_wallet()
    output = _run_new_plugin(oracle)
    chunks = _parse_section_chunks(output)
    rows = chunks.get("oracle_instance", [])
    assert rows, f"No oracle_instance rows under wallet auth:\n{output}"
    for row in rows:
        assert "FAILURE" not in row and "ERROR:" not in row, (
            f"Wallet auth produced a failure row: {row}"
        )
    _assert_rows_start_with_sid(rows, oracle.SID)


@pytest.mark.parametrize("auth_mode", ["wallet", "credential"])
def test_docker_oracle(
    oracle: OracleDatabase,
    auth_mode: Literal["wallet", "credential"],
) -> None:
    if auth_mode == "wallet":
        oracle.use_wallet()
    else:
        oracle.use_credentials()
    rc, output = oracle.container.exec_run([oracle.cmk_plugin.as_posix(), "-t"], user="root")
    assert isinstance(output, bytes)  # stream/socket/demux not used above
    agent_plugin_output = output.decode("utf-8")
    assert rc == 0 and "test login works" in agent_plugin_output, (
        f"Oracle plugin could not connect to database using {auth_mode} authentication!\n"
        f"{agent_plugin_output}"
    )
    rc, output = oracle.container.exec_run(
        f"""bash -c '{oracle.cmk_plugin.as_posix()}'""", user="root"
    )
    assert isinstance(output, bytes)  # stream/socket/demux not used above
    agent_plugin_output = output.decode("utf-8")
    assert rc == 0, f"Oracle plugin failed!\n{agent_plugin_output}"

    all_sections, error_sections, non_empty_sections = _parse_oracle_sections(agent_plugin_output)

    assert len(error_sections) == 0, f"Sections with errors: {error_sections}"

    expected_non_empty_sections = [
        "oracle_instance",
        "oracle_sessions",
        "oracle_logswitches",
        "oracle_undostat",
        "oracle_processes",
        "oracle_recovery_status",
        "oracle_longactivesessions",
        "oracle_performance",
        "oracle_locks",
        "oracle_systemparameter",
        "oracle_instance",
        "oracle_processes",
    ]
    expected_sections = expected_non_empty_sections + [
        "oracle_recovery_area",
        "oracle_dataguard_stats",
        "oracle_tablespaces",
        "oracle_rman",
        "oracle_jobs",
        "oracle_resumable",
        "oracle_iostats",
        "oracle_asm_diskgroup",
    ]

    missing_sections = [_ for _ in expected_sections if _ not in all_sections]
    assert len(missing_sections) == 0, f"Missing sections from agent output: {missing_sections}"

    missing_non_empty_sections = [
        _ for _ in expected_non_empty_sections if _ not in non_empty_sections
    ]
    assert len(missing_non_empty_sections) == 0, (
        f"Missing non-empty sections from agent output: {missing_non_empty_sections}"
    )


# ---------------------------------------------------------------------------
# TC-ORA-700: legacy → new configuration migration
# ---------------------------------------------------------------------------

_MIGRATION_METRIC: Final[str] = "migrationtest"
_MIGRATION_SQL_FILE: Final[str] = "migration_check.sql"
# One constant row: the harness compares custom-SQL rows by full line, so the
# query must produce identical text under sqlplus (old) and the Rust driver (new).
_MIGRATION_SQL: Final[str] = "SELECT 'mig_marker' || ':' || 'const_value' FROM dual;\n"


def _migration_sql_dir(oracle: OracleDatabase) -> Path:
    return oracle.cmk_cfg_dir / "custom_sqls"


def _legacy_migration_cfg(oracle: OracleDatabase) -> str:
    """A minimal legacy mk_oracle.cfg plus one custom SQL section."""
    return "\n".join(
        [
            "MAX_TASKS=10",
            f"DBUSER='{oracle.cmk_username}:{oracle.cmk_password}"
            f"::localhost:{oracle.PORT}:{oracle.SID}'",
            f"TNS_ADMIN={oracle.tns_admin_dir.as_posix()}",
            "",
            f'SQLS_SECTIONS="{_MIGRATION_METRIC}"',
            f"{_MIGRATION_METRIC}() {{",
            f"    SQLS_DIR={_migration_sql_dir(oracle).as_posix()}",
            f"    SQLS_SQL={_MIGRATION_SQL_FILE}",
            f'    SQLS_SIDS="{oracle.SID}"',
            # Align the [[[<sid>|<item>]]] marker: the legacy default item is the
            # SQL *file name*, while the converter names the metric after the
            # section function.
            f"    SQLS_ITEM_NAME={_MIGRATION_METRIC}",
            "}",
        ]
    )


def _install_legacy_migration_setup(oracle: OracleDatabase) -> None:
    """Install the custom SQL file and activate the legacy config in the container."""
    sql_dir = _migration_sql_dir(oracle)
    rc, output = oracle.container.exec_run(rf'mkdir -p "{sql_dir.as_posix()}"', user="root")
    assert rc == 0, f'Could not create "{sql_dir}"! Reason: {output!r}'

    sql_host_path = oracle.ORAENV / _MIGRATION_SQL_FILE
    sql_host_path.write_text(_MIGRATION_SQL, encoding="UTF-8")
    assert copy_to_container(oracle.container, sql_host_path, sql_dir), (
        f'Failed to copy "{_MIGRATION_SQL_FILE}" to container'
    )

    cfg_host_path = oracle.ORAENV / "mk_oracle.migration.cfg"
    cfg_host_path.write_text(_legacy_migration_cfg(oracle), encoding="UTF-8")
    assert copy_to_container(oracle.container, cfg_host_path, oracle.cmk_cfg_dir), (
        "Failed to copy the legacy migration config to container"
    )
    rc, output = oracle.container.exec_run(
        rf'cp "{(oracle.cmk_cfg_dir / cfg_host_path.name).as_posix()}" "{oracle.cmk_cfg.as_posix()}"',
        user="root",
    )
    assert isinstance(output, bytes)  # stream/socket/demux not used above
    assert rc == 0, f"Failed to activate legacy config: {output.decode('UTF-8')}"


def _migrate_legacy_config(oracle: OracleDatabase) -> Path:
    """Convert the legacy config with the mk-oracle converter; assert a clean run."""
    migrated_path = oracle.cmk_cfg_dir / "mk-oracle.migrated.yml"
    rc, output = oracle.container.exec_run(
        [
            oracle.new_plugin.as_posix(),
            "--migrate-config",
            oracle.cmk_cfg.as_posix(),
            "--migrate-output",
            migrated_path.as_posix(),
        ],
        user="root",
    )
    assert isinstance(output, bytes)  # stream/socket/demux not used above
    text = output.decode("utf-8")
    # "No silent errors during conversion": clean exit and no converter warnings
    # (the SQL file contains no sqlplus-only directives).
    assert rc == 0, f"Migration failed (rc={rc})!\n{text}"
    assert "WARNING" not in text, f"Migration produced warnings:\n{text}"

    rc, output = oracle.container.exec_run(["cat", migrated_path.as_posix()])
    assert isinstance(output, bytes)  # stream/socket/demux not used above
    yml = output.decode("utf-8")
    assert rc == 0, f"Cannot read migrated config: {yml}"
    assert "# WARNING" not in yml, f"Migrated config carries warnings:\n{yml}"
    assert f"- sid: {oracle.SID}" in yml, f"Missing instance entry:\n{yml}"
    assert f"- {_MIGRATION_METRIC}:" in yml, f"Missing custom metric entry:\n{yml}"
    assert f"path: {(_migration_sql_dir(oracle) / _MIGRATION_SQL_FILE).as_posix()}" in yml, (
        f"Missing custom metric SQL path:\n{yml}"
    )
    return migrated_path


def _strip_elapsed_rows(output: str) -> str:
    """Drop the ``elapsed:<seconds>`` rows the old plugin appends to custom SQL sections.

    Its value is volatile between runs, so it can never compare
    equal and is removed from the old output before comparison.
    """
    return "\n".join(line for line in output.splitlines() if not line.startswith("elapsed:"))


def _assert_migration_drop_in(oracle: OracleDatabase) -> None:
    """TC-ORA-700 harness: legacy run vs migrated-config run must be drop-in compatible."""
    oracle.use_credentials()  # baseline sqlnet.ora (no wallet override)
    _install_legacy_migration_setup(oracle)

    old_output = _strip_elapsed_rows(run_old_plugin(oracle))
    custom_marker = f"[[[{oracle.SID}|{_MIGRATION_METRIC}]]]"
    assert custom_marker in old_output, (
        f"Old plugin did not emit the custom SQL section:\n{old_output}"
    )

    migrated_path = _migrate_legacy_config(oracle)
    new_output = _run_new_plugin(oracle, migrated_path)
    assert custom_marker in new_output, (
        f"New plugin did not emit the migrated custom metric:\n{new_output}"
    )

    # Drop-in bar: the TC-ORA-002 per-section comparison (section set, per-section
    # row-key set and per-key column count; values beyond the key are ignored).
    # No migration-specific deviations are accepted beyond the TC-ORA-002 baseline.
    comparison = ComparisonResult(PluginOutput(old_output), PluginOutput(new_output))
    # Printed output is captured by pytest and only shown on failure.
    comparison.print_summary()
    comparison.print_detailed(show_diff=True)

    unexpected_only_in_old = sorted(set(comparison.only_in_old) - KNOWN_DEVIATIONS["only_in_old"])
    unexpected_only_in_new = sorted(set(comparison.only_in_new) - KNOWN_DEVIATIONS["only_in_new"])
    unexpected_different = sorted(set(comparison.different) - KNOWN_DEVIATIONS["different"])

    assert not (unexpected_only_in_old or unexpected_only_in_new or unexpected_different), (
        "Unexpected pre- vs post-migration differences (not in the accepted deviations):\n"
        f"  only in old (mk_oracle): {unexpected_only_in_old}\n"
        f"  only in new (mk-oracle): {unexpected_only_in_new}\n"
        f"  differing content:       {unexpected_different}\n"
        "See the captured comparison output above for the section-level diff."
    )


def test_legacy_config_migration(oracle: OracleDatabase) -> None:
    """TC-ORA-700 (single-instance CDB): migrate a legacy mk_oracle.cfg with one
    custom SQL section and compare pre- vs post-migration agent output."""
    _assert_migration_drop_in(oracle)


# ---------------------------------------------------------------------------
# PDB filtering tests — require extra PDBs created in the container
# ---------------------------------------------------------------------------


@pytest.fixture(name="oracle_with_pdbs", scope="session")
def _oracle_with_pdbs(oracle: OracleDatabase) -> OracleDatabase:
    """Extend the Oracle fixture with extra PDBs for PDB filtering tests."""
    sql = "\n".join(
        [
            "WHENEVER SQLERROR EXIT SQL.SQLCODE",
            # Enable Oracle Managed Files so PDB datafiles can be placed automatically.
            # The Oracle Free Docker container ships with db_create_file_dest unset.
            "ALTER SYSTEM SET DB_CREATE_FILE_DEST='/opt/oracle/oradata/FREE' SCOPE=BOTH;",
            f"GRANT SET CONTAINER TO {oracle.cmk_username} CONTAINER=ALL;",
            "CREATE PLUGGABLE DATABASE TESTPDB1 ADMIN USER admin IDENTIFIED BY admin;",
            "ALTER PLUGGABLE DATABASE TESTPDB1 OPEN;",
            "CREATE PLUGGABLE DATABASE TESTPDB2 ADMIN USER admin IDENTIFIED BY admin;",
            "ALTER PLUGGABLE DATABASE TESTPDB2 OPEN;",
            "CREATE PLUGGABLE DATABASE DEVPDB1 ADMIN USER admin IDENTIFIED BY admin;",
            "ALTER PLUGGABLE DATABASE DEVPDB1 OPEN;",
            "EXIT;",
        ]
    )
    sql_path = oracle.ORAENV / "create_pdbs.sql"
    sql_path.write_text(sql, encoding="utf-8")
    container_sql_path = oracle.ROOT / "create_pdbs.sql"
    assert copy_to_container(oracle.container, sql_path, oracle.ROOT), (
        "Failed to copy create_pdbs.sql to container"
    )
    rc, output = oracle.container.exec_run(
        f"""bash -c 'sqlplus -s "/ as sysdba" < "{container_sql_path.as_posix()}"'""",
        user="oracle",
    )
    assert isinstance(output, bytes)  # stream/socket/demux not used above
    assert rc == 0, f"Failed to create extra PDBs: {output.decode('utf-8')}"
    return oracle


def _pdb_config_yml(oracle: OracleDatabase, pdbs: list[str]) -> str:
    pdbs_str = ", ".join(f'"{p}"' for p in pdbs)
    return "\n".join(
        [
            "---",
            "oracle:",
            "  main:",
            "    authentication:",
            f"      username: {oracle.cmk_username}",
            f"      password: {oracle.cmk_password}",
            "      type: standard",
            "    connection:",
            "      hostname: localhost",
            f"      port: {oracle.PORT}",
            "      timeout: 15",
            f"      service_name: {oracle.SID}",
            "    custom_metrics:",
            "      - container_identity:",
            "          sql: \"SELECT SYS_CONTEXT('USERENV', 'CON_NAME') FROM DUAL\"",
            f"          pdbs: [{pdbs_str}]",
        ]
    )


def test_pdb_exact_names_produce_correct_subsections(oracle_with_pdbs: OracleDatabase) -> None:
    oracle = oracle_with_pdbs
    cfg_path = _install_custom_config(
        oracle, _pdb_config_yml(oracle, ["TESTPDB1", "TESTPDB2"]), "mk-oracle.pdb-exact.yml"
    )
    output = _run_new_plugin(oracle, cfg_path)
    assert f"{oracle.SID}_TESTPDB1|container_identity" in output, (
        f"missing TESTPDB1 subsection: {output}"
    )
    assert f"{oracle.SID}_TESTPDB2|container_identity" in output, (
        f"missing TESTPDB2 subsection: {output}"
    )
    assert f"{oracle.SID}_DEVPDB1" not in output, f"DEVPDB1 must not appear: {output}"
    assert f"{oracle.SID}_FREEPDB1" not in output, f"FREEPDB1 must not appear: {output}"


def test_pdb_regex_matches_only_test_pdbs(oracle_with_pdbs: OracleDatabase) -> None:
    oracle = oracle_with_pdbs
    cfg_path = _install_custom_config(
        oracle, _pdb_config_yml(oracle, ["TEST.*"]), "mk-oracle.pdb-regex.yml"
    )
    output = _run_new_plugin(oracle, cfg_path)
    assert f"{oracle.SID}_TESTPDB1|container_identity" in output, f"missing TESTPDB1: {output}"
    assert f"{oracle.SID}_TESTPDB2|container_identity" in output, f"missing TESTPDB2: {output}"
    assert f"{oracle.SID}_DEVPDB1" not in output, f"DEVPDB1 must not appear: {output}"
    assert f"{oracle.SID}_FREEPDB1" not in output, f"FREEPDB1 must not appear: {output}"


def test_legacy_config_migration_multi_pdb(oracle_with_pdbs: OracleDatabase) -> None:
    """TC-ORA-700 (multi-PDB CDB): the same legacy → new migration comparison
    against a CDB that carries several extra PDBs."""
    _assert_migration_drop_in(oracle_with_pdbs)
