#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""measure.py — Single-run Oracle plugin performance measurement. See README.md."""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime, UTC
from pathlib import Path
from typing import NamedTuple

SCRIPT_DIR = Path(__file__).parent

SECTIONS: list[str] = [
    "instance",
    "sessions",
    "logswitches",
    "undostat",
    "recovery_area",
    "processes",
    "recovery_status",
    "longactivesessions",
    "dataguard_stats",
    "performance",
    "locks",
    "systemparameter",
    "tablespaces",
    "rman",
    "jobs",
    "resumable",
    "iostats",
]
TNS_ALIAS = "PERF_POOLED"


class Config(NamedTuple):
    host: str
    port: int
    user: str
    password: str
    service: str
    tns_dir: str = ""


class Bins(NamedTuple):
    rust: str
    legacy: str
    oci_lib_dir: str
    libaio_compat_dir: str


class Timing(NamedTuple):
    scenario: str
    section: str
    plugin: str
    run: int
    wall_ms: float


def main() -> None:
    parser = argparse.ArgumentParser(description="Oracle plugin performance measurement")
    parser.add_argument("--scenario", choices=["standard", "batched"], default="standard")
    parser.add_argument("--runs", type=int, default=3, help="Timed runs per point (min 3)")
    parser.add_argument("--label", default=os.environ.get("LABEL", ""), help="Output CSV label")
    parser.add_argument(
        "--use-legacy",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run the legacy mk_oracle plugin (default: on; --no-use-legacy to skip)",
    )
    parser.add_argument(
        "--env-file", type=Path, metavar="FILE", help=".env file with PERF_DB_* vars"
    )
    parser.add_argument(
        "--sleep-between-runs",
        type=float,
        default=0.0,
        metavar="SECS",
        help="Sleep after each timed invocation to reduce variance under load",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=1,
        metavar="N",
        help="Thread count for parallel query execution (default: 1 = sequential)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help="Directory for the output CSV (default: runs/ next to this script)",
    )
    args = parser.parse_args()

    runs = max(3, args.runs)
    if runs != args.runs:
        print(f"NOTE: --runs raised to minimum of {runs}")

    label = args.label or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir or (SCRIPT_DIR / "runs")
    output_csv = output_dir / f"{label}.csv"
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    cfg = load_config(env_file_override=args.env_file)
    bins = resolve_bins(use_legacy=args.use_legacy)
    sleep_secs = args.sleep_between_runs

    print(f"Scenario:  {args.scenario}")
    print(f"Runs:      {runs}")
    if sleep_secs > 0:
        print(f"Sleep:     {sleep_secs:.1f}s between runs")
    print(f"Rust:      {bins.rust}")
    print(f"Legacy:    {bins.legacy or '(skipped)'}")
    print(f"Target:    {cfg.user}@{cfg.host}:{cfg.port}/{cfg.service}")
    if cfg.tns_dir:
        print(f"TNS:       {cfg.tns_dir} (alias {TNS_ALIAS})")
    print(f"Output:    {output_csv}")
    print()

    if args.threads > 1:
        print(f"Threads:   {args.threads}")
    if args.scenario == "standard":
        results = run_standard(cfg, bins, runs, sleep_secs=sleep_secs, threads=args.threads)
    else:
        results = run_batched(cfg, bins, runs, sleep_secs=sleep_secs, threads=args.threads)

    print_summary(results)
    print_winner_summary(results)
    write_csv(results, output_csv)
    print(f"\nDone. Results: {output_csv}")


# ---------------------------------------------------------------------------
# Scenario runners
# ---------------------------------------------------------------------------


def run_standard(
    cfg: Config, bins: Bins, runs: int, sleep_secs: float = 0.0, threads: int = 1
) -> list[Timing]:
    results: list[Timing] = []
    sleep_note = f", {sleep_secs:.1f}s sleep between runs" if sleep_secs > 0 else ""
    print(f"  {len(SECTIONS)} sections timed individually (is_async: no{sleep_note})", flush=True)
    print(flush=True)
    for section in SECTIONS:
        print(f"  {section}", flush=True)
        for run in range(1, runs + 1):
            ms = _rust_timed(cfg, bins, [section], threads=threads)
            results.append(Timing("standard", section, "rust", run, ms))
            print(_fmt_run(run, runs, "rust", ms))
            if sleep_secs > 0:
                time.sleep(sleep_secs)
        if bins.legacy:
            for run in range(1, runs + 1):
                ms = _legacy_timed(cfg, bins, section=section)
                results.append(Timing("standard", section, "legacy", run, ms))
                print(_fmt_run(run, runs, "legacy", ms))
                if sleep_secs > 0:
                    time.sleep(sleep_secs)
    return results


def run_batched(
    cfg: Config, bins: Bins, runs: int, sleep_secs: float = 0.0, threads: int = 1
) -> list[Timing]:
    results: list[Timing] = []
    sleep_note = f", {sleep_secs:.1f}s sleep between runs" if sleep_secs > 0 else ""
    print(
        f"  all {len(SECTIONS)} sections in one invocation (is_async: no{sleep_note})", flush=True
    )
    print(flush=True)
    for run in range(1, runs + 1):
        ms = _rust_timed(cfg, bins, SECTIONS, threads=threads)
        results.append(Timing("batched", "all_sections_batched", "rust", run, ms))
        print(_fmt_run(run, runs, "rust", ms))
        if sleep_secs > 0:
            time.sleep(sleep_secs)
    if bins.legacy:
        for run in range(1, runs + 1):
            ms = _legacy_timed(cfg, bins, sync_sections=SECTIONS)
            results.append(Timing("batched", "all_sections_batched", "legacy", run, ms))
            print(_fmt_run(run, runs, "legacy", ms))
            if sleep_secs > 0:
                time.sleep(sleep_secs)
    return results


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def print_summary(results: list[Timing]) -> None:
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for t in results:
        grouped[(t.scenario, t.section, t.plugin)].append(t.wall_ms)

    avgs: dict[tuple[str, str, str], float] = {k: statistics.mean(v) for k, v in grouped.items()}
    scenarios_sections: dict[str, list[str]] = defaultdict(list)
    for scenario, section, _ in grouped:
        if section not in scenarios_sections[scenario]:
            scenarios_sections[scenario].append(section)

    print()
    print(f"{'Section':<30} {'Plugin':<10} {'Min':>9} {'Avg':>9} {'Max':>9}  {'Delta':>8}  Winner")
    print(f"{'-------':<30} {'------':<10} {'---':>9} {'---':>9} {'---':>9}  {'-----':>8}  ------")

    for scenario in [s for s in ("standard", "batched") if s in scenarios_sections]:
        sections = list(scenarios_sections[scenario])

        def _delta_key(section: str, sc: str = scenario) -> float:
            rust = avgs.get((sc, section, "rust"))
            opp = avgs.get((sc, section, "legacy"))
            if rust is None or opp is None:
                return 0.0
            return (rust - opp) / opp

        if scenario == "standard":
            sections = sorted(sections, key=_delta_key, reverse=True)

        print(f"\n  [{scenario}]")
        for section in sections:
            plugins = sorted(
                {p for (sc, sec, p) in grouped if sc == scenario and sec == section},
                key=lambda p: (p == "rust", p),
            )
            rust_avg = avgs.get((scenario, section, "rust"))
            opp_avg = avgs.get((scenario, section, "legacy"))
            delta_pct: float | None = None
            winner: str | None = None
            if rust_avg is not None and opp_avg is not None:
                delta_pct = (rust_avg - opp_avg) * 100.0 / opp_avg
                winner = "rust" if rust_avg <= opp_avg else "legacy"
            for i, plugin in enumerate(plugins):
                mn, avg, mx = _agg(grouped[(scenario, section, plugin)])
                sec_label = section if i == 0 else ""
                delta_str = (
                    f"{delta_pct:>+7.0f}%" if plugin == "rust" and delta_pct is not None else ""
                )
                winner_str = (winner or "") if plugin == "rust" else ""
                print(
                    f"  {sec_label:<28} {plugin:<10} {mn:>8.0f}ms {avg:>8.0f}ms {mx:>8.0f}ms"
                    f"  {delta_str:>8}  {winner_str}"
                )

    std_sections = scenarios_sections.get("standard", [])
    if std_sections:
        std_plugins = sorted({p for (sc, _, p) in grouped if sc == "standard"})
        print()
        print("  Best / Worst per plugin  (standard, by avg):")
        for plugin in std_plugins:
            plugin_avgs = {
                sec: avgs[("standard", sec, plugin)]
                for sec in std_sections
                if ("standard", sec, plugin) in avgs
            }
            if not plugin_avgs:
                continue
            best_sec = min(plugin_avgs, key=lambda k: plugin_avgs[k])
            worst_sec = max(plugin_avgs, key=lambda k: plugin_avgs[k])
            print(f"  {plugin:<10}  fastest: {best_sec:<25} {plugin_avgs[best_sec]:>7.0f}ms avg")
            print(f"  {'':10}  slowest: {worst_sec:<25} {plugin_avgs[worst_sec]:>7.0f}ms avg")


def print_winner_summary(results: list[Timing]) -> None:
    per_key: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for t in results:
        per_key[(t.scenario, t.section, t.plugin)].append(t.wall_ms)

    totals: dict[tuple[str, str], float] = defaultdict(float)
    for (scenario, section, plugin), times in per_key.items():
        totals[(scenario, plugin)] += statistics.mean(times)

    by_scenario: dict[str, dict[str, float]] = defaultdict(lambda: {})
    for (scenario, plugin), total in totals.items():
        by_scenario[scenario][plugin] = total

    print()
    print("=" * 64)
    print("  WINNER SUMMARY  (avg wall-clock; lower is better)")
    print("=" * 64)
    print(f"  {'Scenario':<14} {'Rust':>9} {'Legacy':>12} {'Delta':>8}  Winner")
    print(f"  {'--------':<14} {'----':>9} {'------':>12} {'-----':>8}  ------")

    for scenario in [s for s in ("standard", "batched") if s in by_scenario]:
        plugins = by_scenario[scenario]
        rust_ms = plugins.get("rust")
        legacy_ms = plugins.get("legacy")
        label = scenario + (" *" if scenario == "standard" else "")

        if rust_ms is None or legacy_ms is None:
            only_plugin, only_ms = next(iter(plugins.items()))
            print(
                f"  {label:<14} {'—':>9} {'—':>12} {'—':>8}  {only_plugin} only ({only_ms:.0f}ms)"
            )
        else:
            delta_pct = (rust_ms - legacy_ms) * 100.0 / legacy_ms
            winner = "rust" if rust_ms <= legacy_ms else "legacy"
            print(
                f"  {label:<14} {rust_ms:>8.0f}ms {legacy_ms:>11.0f}ms"
                f" {delta_pct:>+7.0f}%  {winner}"
            )

    n_std = len({sec for (sc, sec, _) in per_key if sc == "standard"})
    if n_std:
        print()
        print(
            f"  * standard = sum of {n_std} section averages "
            f"(one invocation per section; same sections for both plugins)"
        )
    print("=" * 64)


def write_csv(results: list[Timing], output_path: Path) -> None:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with output_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "run", "scenario", "section", "plugin", "wall_ms"])
        for t in results:
            writer.writerow([ts, t.run, t.scenario, t.section, t.plugin, f"{t.wall_ms:.0f}"])


# ---------------------------------------------------------------------------
# Configuration and binary resolution
# ---------------------------------------------------------------------------


def load_config(env_file_override: Path | None = None) -> Config:
    env_file = env_file_override or (SCRIPT_DIR / ".env")
    exports_file = SCRIPT_DIR / "../../../../exports.sh"

    if env_file.exists():
        env = _source_env_file(env_file)
        for key in ("MK_ORACLE_BIN", "MK_ORACLE_LEGACY", "OCI_LIB_DIR"):
            if key in env:
                os.environ[key] = env[key]
        return Config(
            host=env.get("PERF_DB_HOST", "localhost"),
            port=int(env.get("PERF_DB_PORT", "1521")),
            user=env.get("PERF_DB_USER", "system"),
            password=env["PERF_DB_PASSWORD"],
            service=env.get("PERF_DB_SERVICE", "FREEPDB1"),
            tns_dir=env.get("PERF_TNS_DIR", ""),
        )
    elif exports_file.exists():
        env = _source_env_file(exports_file)
        return Config(
            host=env.get("DB_HOST", "localhost"),
            port=int(env.get("DB_PORT", "1521")),
            user=env.get("DB_USER", "system"),
            password=env.get("DB_PASSWORD", "oracle"),
            service=env.get("DB_SID", "FREEPDB1"),
        )
    else:
        print(
            "ERROR: no credentials found — run setup.py up or provide exports.sh", file=sys.stderr
        )
        sys.exit(1)


def resolve_bins(*, use_legacy: bool) -> Bins:
    rust_bin = os.environ.get("MK_ORACLE_BIN") or shutil.which("mk-oracle") or ""
    if not rust_bin:
        print(
            "ERROR: mk-oracle binary not found — run ./install.sh first or set MK_ORACLE_BIN",
            file=sys.stderr,
        )
        sys.exit(1)

    legacy = ""
    if use_legacy:
        legacy_default = SCRIPT_DIR / "../../../../agents/plugins/mk_oracle"
        legacy_path = Path(os.environ.get("MK_ORACLE_LEGACY", str(legacy_default)))
        if legacy_path.is_file() and os.access(legacy_path, os.X_OK):
            legacy = str(legacy_path)
        else:
            print(f"WARNING: legacy plugin not found at {legacy_path}", file=sys.stderr)

    oci_lib_dir = os.environ.get("OCI_LIB_DIR", "")
    if not oci_lib_dir:
        print("WARNING: OCI_LIB_DIR not set — run ./install.sh or set it manually", file=sys.stderr)

    # Ubuntu 24+: libaio.so.1 was renamed to libaio.so.1t64. Create a compat symlink
    # so Oracle Instant Client can find it under its expected name.
    libaio_compat_dir = ""
    if not Path("/usr/lib/x86_64-linux-gnu/libaio.so.1").exists():
        src = next(Path("/usr/lib").glob("**/libaio.so.1t64"), None)
        if src:
            compat = Path("/tmp/mk_oracle_libaio_compat")
            compat.mkdir(exist_ok=True)
            link = compat / "libaio.so.1"
            if not link.exists():
                link.symlink_to(src)
            libaio_compat_dir = str(compat)

    return Bins(
        rust=rust_bin,
        legacy=legacy,
        oci_lib_dir=oci_lib_dir,
        libaio_compat_dir=libaio_compat_dir,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _rust_timed(cfg: Config, bins: Bins, sections: list[str], threads: int = 1) -> float:
    yaml_text = _rust_config(cfg, bins, sections, threads=threads)
    env = _base_env(bins)
    tmp_var = tempfile.mkdtemp(prefix="mk_oracle_var_")
    env["MK_VARDIR"] = tmp_var
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yml", prefix="mk_oracle_perf_", delete=False
    ) as f:
        f.write(yaml_text)
        cfg_path = f.name
    try:
        t0 = time.perf_counter()
        subprocess.run(
            [bins.rust, "--config-file", cfg_path], env=env, capture_output=True, check=True
        )
        return (time.perf_counter() - t0) * 1000.0
    finally:
        Path(cfg_path).unlink(missing_ok=True)
        shutil.rmtree(tmp_var, ignore_errors=True)


def _legacy_timed(
    cfg: Config,
    bins: Bins,
    section: str | None = None,
    sync_sections: list[str] | None = None,
) -> float:
    conf_dir, var_dir = _setup_legacy_dirs()
    cfg_file = Path(conf_dir) / "mk_oracle.cfg"
    if sync_sections is not None:
        cfg_file.write_text('SYNC_SECTIONS="' + " ".join(sync_sections) + "\"\nASYNC_SECTIONS=''\n")
    else:
        cfg_file.unlink(missing_ok=True)
    env = _legacy_env(cfg, bins, conf_dir, var_dir)
    cmd = [bins.legacy, "--no-spool"]
    if section is not None:
        cmd += ["--sections", section]
    t0 = time.perf_counter()
    subprocess.run(cmd, env=env, capture_output=True, check=True)
    return (time.perf_counter() - t0) * 1000.0


def _base_env(bins: Bins) -> dict[str, str]:
    env = os.environ.copy()
    ld_parts = [p for p in (bins.libaio_compat_dir, bins.oci_lib_dir) if p]
    if existing := env.get("LD_LIBRARY_PATH"):
        ld_parts.append(existing)
    if ld_parts:
        env["LD_LIBRARY_PATH"] = ":".join(ld_parts)
    return env


def _legacy_env(cfg: Config, bins: Bins, conf_dir: str, var_dir: str) -> dict[str, str]:
    env = _base_env(bins)
    sid_upper = cfg.service.upper()
    env[f"REMOTE_INSTANCE_{sid_upper}"] = (
        f"{cfg.user}:{cfg.password}::{cfg.host}:{cfg.port}::{cfg.service}::"
    )
    env["ID_BY"] = "SERVICE_NAME"
    env["MK_CONFDIR"] = conf_dir
    env["MK_VARDIR"] = var_dir
    if bins.oci_lib_dir:
        env["ORACLE_HOME"] = bins.oci_lib_dir
        env["REMOTE_ORACLE_HOME"] = bins.oci_lib_dir
        env["PATH"] = f"{bins.oci_lib_dir}:{env.get('PATH', '')}"
    return env


def _setup_legacy_dirs() -> tuple[str, str]:
    conf_dir = "/tmp/mkoravar_perf_conf"
    var_dir = "/tmp/mkoravar_perf"
    Path(conf_dir).mkdir(parents=True, exist_ok=True)
    shutil.rmtree(var_dir, ignore_errors=True)
    Path(var_dir).mkdir(parents=True, exist_ok=True)
    sqlnet_ora = Path(conf_dir) / "sqlnet.ora"
    if not sqlnet_ora.exists():
        sqlnet_ora.write_text("SQLNET.AUTHENTICATION_SERVICES = (NONE)\n")
    return conf_dir, var_dir


def _rust_config(cfg: Config, bins: Bins, sections: list[str], threads: int = 1) -> str:
    oci = bins.oci_lib_dir or ""
    section_lines = [f"- {s}:\n          is_async: no" for s in sections]
    sections_block = "      " + "\n      ".join(section_lines) if section_lines else "      []"

    if cfg.tns_dir:
        conn_block = f"    connection:\n      tns_admin: {cfg.tns_dir}\n    alias: {TNS_ALIAS}\n"
    else:
        conn_block = (
            f"    connection:\n"
            f"      hostname: {cfg.host}\n"
            f"      port: {cfg.port}\n"
            f"      service_name: {cfg.service}\n"
        )

    threads_line = f"      threads: {threads}\n" if threads > 1 else ""

    return (
        f"---\n"
        f"oracle:\n"
        f"  main:\n"
        f"    options:\n"
        f'      use_host_client: "{oci}"\n'
        f"{threads_line}"
        f"    authentication:\n"
        f"      username: {cfg.user}\n"
        f"      password: {cfg.password}\n"
        f"      type: standard\n"
        f"    discovery:\n"
        f"      detect: no\n"
        f"{conn_block}"
        + (f"    instances:\n      - service_name: {cfg.service}\n" if sections else "")
        + f"    sections:\n"
        f"{sections_block}\n"
    )


def _source_env_file(path: Path) -> dict[str, str]:
    result = subprocess.run(
        ["bash", "-c", f"source {path} && env"], capture_output=True, text=True, check=False
    )
    out: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            out[k] = v
    return out


def _fmt_run(run: int, runs: int, plugin: str, ms: float) -> str:
    return f"    [{run}/{runs}] {plugin:<8} {ms:>8.0f}ms"


def _agg(timings: list[float]) -> tuple[float, float, float]:
    return min(timings), statistics.mean(timings), max(timings)


if __name__ == "__main__":
    main()
