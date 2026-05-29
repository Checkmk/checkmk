#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""bench-phases.py — Full three-phase Oracle benchmark. See README.md."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, UTC
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SWINGBENCH_DIR = SCRIPT_DIR / "swingbench"
LOAD_SETTLE_SECS = 60

DB_HOST = "localhost"
DB_PORT = 15210
DB_SERVICE = "FREEPDB1"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Three-phase Oracle performance benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Timed runs per measurement point (default: 5)",
    )
    parser.add_argument(
        "--uc",
        type=int,
        default=50,
        help="charbench virtual user count for phase 3 (default: 50)",
    )
    parser.add_argument(
        "--use-legacy",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run the legacy mk_oracle plugin (default: on; --no-use-legacy to skip)",
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        default=["standard", "batched"],
        choices=["standard", "batched"],
        help="Scenarios to run in each phase (default: standard batched)",
    )
    parser.add_argument(
        "--phases",
        nargs="+",
        default=["empty", "seeded", "load"],
        choices=["empty", "seeded", "load"],
        help="Phases to run (default: empty seeded load). Use --phases load to skip seeding.",
    )
    parser.add_argument(
        "--keep-alive",
        action="store_true",
        help="Do not tear down the container after the run (useful when running back-to-back suites).",
    )
    parser.add_argument(
        "--rman-cycles",
        type=int,
        default=3,
        help="RMAN backup cycles for seeding (default: 3)",
    )
    parser.add_argument(
        "--sleep-between-runs",
        type=float,
        default=0.0,
        metavar="SECS",
        help="Seconds to sleep after each timed invocation (default: 0). Passed to measure.py.",
    )
    parser.add_argument(
        "--prefix",
        default="",
        metavar="STR",
        help="Prefix for result CSV filenames (e.g. 'baseline_direct')",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=1,
        metavar="N",
        help="Thread count for parallel query execution (default: 1 = sequential)",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        metavar="FILE",
        help=".env file with PERF_DB_* vars (use .env.drcp for DRCP)",
    )
    args = parser.parse_args()

    extra = [] if args.use_legacy else ["--no-use-legacy"]
    if args.sleep_between_runs > 0:
        extra += ["--sleep-between-runs", str(args.sleep_between_runs)]
    if args.threads > 1:
        extra += ["--threads", str(args.threads)]
    if args.env_file:
        extra += ["--env-file", str(args.env_file)]

    session = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_name = f"{args.prefix}_{session}" if args.prefix else session
    run_dir = SCRIPT_DIR / "runs" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"Session:   {session}")
    print(f"Run dir:   {run_dir}/")
    print(f"Prefix:    {args.prefix or '(none)'}")
    print(f"Scenarios: {' '.join(args.scenarios)}")
    print(f"Runs/pt:   {args.runs}")
    print(f"VU:        {args.uc}")
    print(f"Legacy:    {'yes' if args.use_legacy else 'no'}")
    print(f"Phases:    {' '.join(args.phases)}")
    if args.sleep_between_runs > 0:
        print(f"Sleep:     {args.sleep_between_runs:.1f}s between runs")
    if args.threads > 1:
        print(f"Threads:   {args.threads}")
    if args.env_file:
        print(f"Env file:  {args.env_file}")
    if args.keep_alive:
        print("Keep-alive: yes (container will not be torn down)")

    # ── Phase 1: empty ───────────────────────────────────────────────────────
    if "empty" in args.phases:
        print("\n\n" + "#" * 60)
        print("# PHASE 1 — empty database (no seeded data, no load)")
        print("#" * 60)
        subprocess.run(["pkill", "-f", "charbench"], check=False)  # clean up any interrupted run
        _setup(run_dir, "down", "--volumes")  # wipe volume so phase 1 is truly empty
        _setup(run_dir, "up", "--no-seed")
        for scenario in args.scenarios:
            _measure(run_dir, scenario, "empty", args.runs, extra)

    # ── Phase 2: seeded (no load) ─────────────────────────────────────────────
    if "seeded" in args.phases:
        print("\n\n" + "#" * 60)
        print("# PHASE 2 — seeded database (100 tablespaces, 500 jobs, RMAN)")
        print("#" * 60)
        _setup(run_dir, "seed-data")
        _setup(run_dir, "seed-rman", "--runs", str(args.rman_cycles))
        for scenario in args.scenarios:
            _measure(run_dir, scenario, "seeded", args.runs, extra)

    # ── Phase 3: seeded + charbench load ─────────────────────────────────────
    if "load" in args.phases:
        print("\n\n" + "#" * 60)
        print(f"# PHASE 3 — seeded + charbench load ({args.uc} VU)")
        print("#" * 60)
        _setup_soe(run_dir)
        charbench_proc = _start_charbench(args.uc, run_dir / "charbench.log")
        try:
            print(f"\nWaiting {LOAD_SETTLE_SECS}s for load to stabilise...", flush=True)
            time.sleep(LOAD_SETTLE_SECS)
            for scenario in args.scenarios:
                _measure(run_dir, scenario, "load", args.runs, extra)
        finally:
            print("Stopping charbench...")
            charbench_proc.terminate()
            try:
                charbench_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                charbench_proc.kill()

    if not args.keep_alive:
        _setup(run_dir, "down")

    # ── Final summary ─────────────────────────────────────────────────────────
    print("\n\n" + "=" * 60)
    print(f"  Session:  {session}")
    print(f"  Run dir:  {run_dir}/")
    print()
    for phase in args.phases:
        for scenario in args.scenarios:
            label = f"{phase}_{scenario}"
            log = run_dir / f"{label}.log"
            status = "ok" if log.exists() else "MISSING"
            print(f"  {label:<30} {status}  log+csv in {run_dir.name}/")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup(run_dir: Path, *args: str) -> None:
    """Run a setup.py subcommand, logging to setup_<args[0]>.log."""
    cmd = [sys.executable, str(SCRIPT_DIR / "setup.py"), *args]
    log_file = run_dir / f"setup_{args[0].replace('-', '_')}.log"
    _run_tee("setup " + " ".join(args), cmd, log_file)


def _measure(run_dir: Path, scenario: str, phase: str, runs: int, extra: list[str]) -> None:
    label = f"{phase}_{scenario}"
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "measure.py"),
        "--scenario",
        scenario,
        "--label",
        label,
        "--output-dir",
        str(run_dir),
        "--runs",
        str(runs),
        *extra,
    ]
    log_file = run_dir / f"{phase}_{scenario}.log"
    _run_tee(f"measure --scenario {scenario}", cmd, log_file)


def _setup_soe(run_dir: Path) -> None:
    """Create the Swingbench SOE schema required by charbench."""
    oewizard = SWINGBENCH_DIR / "bin" / "oewizard"
    if not oewizard.exists():
        print(
            f"  WARNING: {oewizard} not found — skipping SOE schema setup (charbench may fail)",
            file=sys.stderr,
        )
        return
    cmd = [
        str(oewizard),
        "-cs",
        f"//{DB_HOST}:{DB_PORT}/{DB_SERVICE}",
        "-ts",
        "USERS",
        "-u",
        "soe",
        "-p",
        "soe",
        "-dba",
        "system",
        "-dbap",
        os.environ["PERF_DB_PASSWORD"],
        "-create",
        "-scale",
        "0.2",
        "-cl",
    ]
    log_file = run_dir / "setup_soe.log"
    _run_tee("oewizard (SOE schema for charbench)", cmd, log_file)


def _start_charbench(uc: int, log_file: Path) -> subprocess.Popen[bytes]:
    charbench = SWINGBENCH_DIR / "bin" / "charbench"
    if not charbench.exists():
        print(
            f"ERROR: {charbench} not found — run ./install.sh to download Swingbench.",
            file=sys.stderr,
        )
        sys.exit(1)
    connect = f"//{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    config = SWINGBENCH_DIR / "configs" / "SOE_Server_Side_V2.xml"
    print(f"Starting charbench with {uc} virtual users (log: {log_file})...")
    with open(log_file, "w") as log:
        proc = subprocess.Popen(
            [
                str(charbench),
                "-cs",
                connect,
                "-u",
                "soe",
                "-p",
                "soe",
                "-uc",
                str(uc),
                "-rt",
                "12:00",
                "-c",
                str(config),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    print(f"  charbench PID {proc.pid}")
    return proc


def _run_tee(header: str, cmd: list[str], log_file: Path) -> None:
    """Run cmd, tee stdout+stderr to log_file and the terminal simultaneously."""
    print(f"\n{'=' * 60}", flush=True)
    print(f"  {header}", flush=True)
    print(f"  log → {log_file}", flush=True)
    print(f"{'=' * 60}", flush=True)

    with log_file.open("wb") as f:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.buffer.write(line)
            f.write(line)
        sys.stdout.buffer.flush()
        proc.wait()

    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)


if __name__ == "__main__":
    main()
