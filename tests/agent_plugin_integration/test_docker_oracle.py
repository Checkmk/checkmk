#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from pathlib import Path
from typing import Final, Literal

import pytest

from tests.agent_plugin_integration.conftest import OracleDatabase
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
    text: str = output.decode("utf-8")
    assert rc == 0, f"mk-oracle plugin failed!\n{text}"
    return text


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
    agent_plugin_output = output.decode("utf-8")
    assert rc == 0 and "test login works" in agent_plugin_output, (
        f"Oracle plugin could not connect to database using {auth_mode} authentication!\n"
        f"{agent_plugin_output}"
    )
    rc, output = oracle.container.exec_run(
        f"""bash -c '{oracle.cmk_plugin.as_posix()}'""", user="root"
    )
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
