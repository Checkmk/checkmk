#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""setup.py — Oracle container and seed management. See README.md."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
COMPOSE_FILE = SCRIPT_DIR / "docker-compose.yml"
CONTAINER = "oracle-perf"
ENV_FILE = SCRIPT_DIR / ".env"

DB_HOST = "localhost"
DB_PORT = 15210
DB_USER = "system"
DB_PASSWORD = os.environ["PERF_DB_PASSWORD"]
DB_SERVICE = "FREEPDB1"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Oracle performance test environment management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_up = sub.add_parser("up", help="Start container, seed test data, and run RMAN cycles")
    p_up.add_argument(
        "--no-seed",
        action="store_true",
        help="Skip data seeding and RMAN (for bench-phases.py phase 1)",
    )
    p_up.add_argument(
        "--runs",
        type=int,
        default=3,
        metavar="N",
        help="RMAN backup cycles (default: 3)",
    )

    sub.add_parser("seed-data", help="Seed 100 tablespaces + 500 scheduler jobs (requires up)")

    p_rman = sub.add_parser(
        "seed-rman",
        help="Enable ARCHIVELOG mode and run RMAN backup cycles to populate V$ views",
    )
    p_rman.add_argument(
        "--runs",
        type=int,
        default=3,
        metavar="N",
        help="Number of RMAN backup cycles to run (default: 3)",
    )

    p_down = sub.add_parser("down", help="Stop the Oracle container")
    p_down.add_argument(
        "--volumes",
        "-v",
        action="store_true",
        help="Also remove the data volume (wipes the database — use before bench-phases.py)",
    )

    args = parser.parse_args()

    if args.command == "up":
        cmd_up(seed=not args.no_seed, runs=args.runs)
    elif args.command == "seed-data":
        cmd_seed_data()
    elif args.command == "seed-rman":
        cmd_seed_rman(args.runs)
    elif args.command == "down":
        cmd_down(volumes=args.volumes)


def cmd_up(seed: bool = True, runs: int = 3) -> None:
    print(f"Starting {CONTAINER} container...")
    _compose("up", "-d", CONTAINER)
    _wait_healthy("Oracle Free 23c")

    print("Setting PROCESSES=600 and restarting Oracle...")
    _sqlplus("ALTER SYSTEM SET PROCESSES=600 SCOPE=SPFILE;\nSHUTDOWN IMMEDIATE;\nSTARTUP;\nEXIT;\n")

    time.sleep(5)
    _wait_healthy("Oracle after restart")

    if seed:
        _seed_data()

    print("Adding 200MB redo log groups (prevents log file switch stalls under load)...")
    _sqlplus(
        "ALTER DATABASE ADD LOGFILE GROUP 3 '/opt/oracle/oradata/FREE/redo03.log' SIZE 200M;\n"
        "ALTER DATABASE ADD LOGFILE GROUP 4 '/opt/oracle/oradata/FREE/redo04.log' SIZE 200M;\n"
        "ALTER DATABASE ADD LOGFILE GROUP 5 '/opt/oracle/oradata/FREE/redo05.log' SIZE 200M;\n"
        "ALTER SYSTEM SWITCH LOGFILE;\n"
        "ALTER SYSTEM SWITCH LOGFILE;\n"
        "ALTER SYSTEM SWITCH LOGFILE;\n"
        "EXIT;\n"
    )

    print("Starting DRCP connection pool...")
    _sqlplus("EXECUTE DBMS_CONNECTION_POOL.START_POOL();\nEXIT;\n")

    _update_env(
        PERF_DB_HOST=DB_HOST,
        PERF_DB_PORT=str(DB_PORT),
        PERF_DB_USER=DB_USER,
        PERF_DB_PASSWORD=DB_PASSWORD,
        PERF_DB_SERVICE=DB_SERVICE,
    )

    if seed:
        cmd_seed_rman(runs)

    print()
    print("Setup complete.")
    print(f"  Host:    {DB_HOST}:{DB_PORT}")
    print(f"  Service: {DB_SERVICE}")
    print(f"  User:    {DB_USER} / {DB_PASSWORD}")
    if not seed:
        print("  NOTE: seeding skipped (--no-seed); run ./setup.py seed-data to add test data")
    print()
    print("Next steps:")
    print("  ./measure.py               # run a quick benchmark")
    print("  ./bench-phases.py          # full three-phase benchmark")


def cmd_seed_data() -> None:
    if not ENV_FILE.exists():
        print("ERROR: .env not found — run ./setup.py up first.", file=sys.stderr)
        sys.exit(1)
    _seed_data()


def cmd_seed_rman(runs: int) -> None:
    if not ENV_FILE.exists():
        print("ERROR: .env not found — run ./setup.py up first.", file=sys.stderr)
        sys.exit(1)

    output = _sqlplus("SELECT log_mode FROM v$database;\nEXIT;\n")
    if "ARCHIVELOG" not in output.upper() or "NOARCHIVELOG" in output.upper():
        print("Database is in NOARCHIVELOG mode — enabling ARCHIVELOG...")
        _sqlplus(
            "SHUTDOWN IMMEDIATE;\n"
            "STARTUP MOUNT;\n"
            "ALTER DATABASE ARCHIVELOG;\n"
            "ALTER DATABASE OPEN;\n"
            "ALTER PLUGGABLE DATABASE ALL OPEN;\n"
            "EXIT;\n"
        )
        time.sleep(5)
        _wait_healthy("Oracle after ARCHIVELOG restart")
        print("ARCHIVELOG mode enabled.")
    else:
        print("Database is already in ARCHIVELOG mode.")

    print("Configuring Fast Recovery Area (2 GB)...")
    _sqlplus(
        "ALTER SYSTEM SET DB_RECOVERY_FILE_DEST_SIZE = 2G SCOPE=BOTH;\n"
        "ALTER SYSTEM SET DB_RECOVERY_FILE_DEST = '/opt/oracle/fast_recovery_area' SCOPE=BOTH;\n"
        "EXIT;\n"
    )

    for i in range(1, runs + 1):
        print(f"Running RMAN backup cycle {i}/{runs} (may take several minutes)...", flush=True)
        _rman(
            "CONFIGURE ARCHIVELOG DELETION POLICY TO NONE;\n"
            "CROSSCHECK ARCHIVELOG ALL;\n"
            "DELETE NOPROMPT EXPIRED ARCHIVELOG ALL;\n"
            "BACKUP DATABASE PLUS ARCHIVELOG;\n"
            "EXIT;\n"
        )
        print(f"  Cycle {i} complete.")

    print()
    print(f"RMAN seeding complete — {runs} backup cycle(s) recorded.")
    print("  v$backup_datafile, v$backup_controlfile_details, v$archived_log are now populated.")


def cmd_down(volumes: bool = False) -> None:
    print("Stopping Oracle container...")
    args = ["down", "-v"] if volumes else ["down"]
    _compose(*args)
    if volumes:
        print("  Volume oracle-perf-data removed — next 'up' starts with an empty database.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compose(*args: str) -> None:
    env = os.environ.copy()
    env["ORACLE_PORT"] = str(DB_PORT)
    subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), *args],
        check=True,
        env=env,
    )


def _sqlplus(sql: str) -> str:
    """Run SQL as sysdba inside the container via stdin, return stdout."""
    result = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "sqlplus", "-s", "/ as sysdba"],
        input=sql.encode(),
        capture_output=True,
        check=True,
    )
    return result.stdout.decode()


def _rman(commands: str) -> None:
    """Run RMAN commands inside the container as the oracle OS user."""
    subprocess.run(
        ["docker", "exec", "--user", "oracle", "-i", CONTAINER, "rman", "target", "/"],
        input=commands.encode(),
        check=True,
    )


def _wait_healthy(label: str = "Oracle", timeout: int = 600) -> None:
    print(f"Waiting for {label} to be healthy...", flush=True)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", CONTAINER],
            capture_output=True,
            text=True,
            check=False,
        )
        status = result.stdout.strip()
        if status == "healthy":
            print(f"{label} is healthy.")
            return
        if status == "unhealthy":
            result = subprocess.run(
                ["docker", "logs", "--tail", "20", CONTAINER],
                capture_output=True,
                text=True,
                check=False,
            )
            print(result.stdout + result.stderr, file=sys.stderr)
            print(f"ERROR: {CONTAINER} is unhealthy", file=sys.stderr)
            sys.exit(1)
        print(f"  status: {status or '(starting)'}", flush=True)
        time.sleep(10)
    print(f"ERROR: timed out waiting for {label} to become healthy", file=sys.stderr)
    sys.exit(1)


def _update_env(**kwargs: str) -> None:
    """Update named export lines in .env, preserving all other lines."""
    existing = ENV_FILE.read_text().splitlines(keepends=True) if ENV_FILE.exists() else []
    prefixes = tuple(f"export {k}=" for k in kwargs)
    preserved = [line for line in existing if not line.startswith(prefixes)]
    new_lines = [f"export {k}={v}\n" for k, v in kwargs.items()]
    ENV_FILE.write_text("".join(preserved + new_lines))


def _seed_data() -> None:
    """Seed 100 tablespaces and 500 scheduler jobs into FREEPDB1."""
    print("Seeding 100 tablespaces in FREEPDB1 (scenario 2)...")
    _sqlplus(
        "ALTER SESSION SET CONTAINER = FREEPDB1;\n"
        "DECLARE\n"
        "  v_sql VARCHAR2(300);\n"
        "BEGIN\n"
        "  FOR i IN 1..100 LOOP\n"
        "    v_sql := 'CREATE TABLESPACE perf_ts_' || LPAD(i, 3, '0')\n"
        "          || ' DATAFILE ''/opt/oracle/oradata/FREE/FREEPDB1/perf_ts_' || LPAD(i, 3, '0') || '.dbf'''\n"
        "          || ' SIZE 7M AUTOEXTEND OFF';\n"
        "    EXECUTE IMMEDIATE v_sql;\n"
        "  END LOOP;\n"
        "END;\n"
        "/\n"
        "EXIT;\n"
    )

    print("Seeding 500 scheduler jobs in FREEPDB1 (scenario 6)...")
    _sqlplus(
        "ALTER SESSION SET CONTAINER = FREEPDB1;\n"
        "BEGIN\n"
        "  FOR i IN 1..500 LOOP\n"
        "    DBMS_SCHEDULER.CREATE_JOB(\n"
        "      job_name   => 'PERF_JOB_' || LPAD(i, 4, '0'),\n"
        "      job_type   => 'PLSQL_BLOCK',\n"
        "      job_action => 'NULL;',\n"
        "      enabled    => FALSE\n"
        "    );\n"
        "  END LOOP;\n"
        "END;\n"
        "/\n"
        "EXIT;\n"
    )


if __name__ == "__main__":
    main()
