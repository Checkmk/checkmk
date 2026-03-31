# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Terminal output helpers for cmk-dev-deploy.

Provides ANSI color constants (auto-disabled when not a TTY), prefixed
message helpers (info, warn, error, success), verbosity-gated display
functions, and per-deployer one-line summary formatting.

Verbosity levels:
  DEFAULT (0): Per-deployer one-liners, service section, errors only.
  VERBOSE (1, -v): Change summaries, target lists, build details.
"""

from __future__ import annotations

import dataclasses
import functools
import io
import os
import re
import sys
import threading
from collections.abc import Callable
from datetime import datetime, UTC
from enum import IntEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any, TYPE_CHECKING

from cmk.dev_deploy.types import ChangeCategory

if TYPE_CHECKING:
    from cmk.dev_deploy.types import (
        BazelTargetSet,
        BuildResult,
        ChangeSet,
        ConfigDeployResult,
        DeployCycleResult,
        Service,
        ServiceAction,
        ServiceResult,
        SiteInfo,
        StepResult,
        WheelDeployResult,
    )


class Verbosity(IntEnum):
    DEFAULT = 0
    VERBOSE = 1  # -v


_ANSI_RE = re.compile(r"\033\[[0-9;]*m")

_SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")


@dataclasses.dataclass
class OutputConfig:
    """All mutable output state consolidated in one place."""

    # Import-time baked values (now overridable via reset())
    use_color: bool = dataclasses.field(default_factory=sys.stdout.isatty)
    is_tty: bool = dataclasses.field(default_factory=sys.stderr.isatty)
    # Runtime-mutable state
    verbosity: Verbosity = Verbosity.DEFAULT
    combined_mode: bool = False
    log_file: io.TextIOWrapper | None = None
    log_file_path: Path | None = None
    # Synchronization
    log_lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)
    output_lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)
    thread_local: threading.local = dataclasses.field(default_factory=threading.local)


_config = OutputConfig()


def _ansi(code: str) -> str:
    """Return *code* when stdout is a TTY, otherwise an empty string."""
    return code if _config.use_color else ""


def _refresh_ansi() -> None:
    """Recompute ANSI color constants from current config."""
    global BOLD, DIM, RED, GREEN, YELLOW, BLUE, RESET
    BOLD = _ansi("\033[1m")
    DIM = _ansi("\033[2m")
    RED = _ansi("\033[31m")
    GREEN = _ansi("\033[32m")
    YELLOW = _ansi("\033[33m")
    BLUE = _ansi("\033[34m")
    RESET = _ansi("\033[0m")


BOLD: str = ""
DIM: str = ""
RED: str = ""
GREEN: str = ""
YELLOW: str = ""
BLUE: str = ""
RESET: str = ""
_refresh_ansi()

# --- Log file (verbose-level, plain text, alongside deploy state) ---


def open_log_file(site_name: str) -> None:
    """Open a deploy log file at ``~/.cmk-dev-deploy/logs/<site>/deploy.log``."""
    log_dir = Path.home() / ".cmk-dev-deploy" / "logs" / site_name
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Fall back to /tmp if home directory is not writable
        log_dir = Path("/tmp/cmk-dev-deploy-logs") / site_name  # nosec B108
        log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    _config.log_file_path = log_dir / f"deploy_{ts}.log"
    _config.log_file = open(_config.log_file_path, "w")


def get_log_file_path() -> Path | None:
    """Return the path of the current log file, or None if not open."""
    return _config.log_file_path


def close_log_file() -> None:
    """Flush and close the deploy log file."""
    if _config.log_file is not None:
        _config.log_file.close()
        _config.log_file = None
    # Keep log_file_path set so diagnostics can still read the log after close


def _log_to_file(msg: str) -> None:
    """Write a plain-text, timestamped line to the log file."""
    if _config.log_file is None:
        return
    plain = _ANSI_RE.sub("", msg)
    ts = datetime.now(tz=UTC).strftime("%H:%M:%S")
    with _config.log_lock:
        _config.log_file.write(f"{ts} {plain}\n")
        _config.log_file.flush()


# --- Verbosity state ---


def set_verbosity(level: int) -> None:
    _config.verbosity = Verbosity(min(level, Verbosity.VERBOSE))


def get_verbosity() -> Verbosity:
    return _config.verbosity


def is_tty() -> bool:
    """Return whether stderr is a TTY (used for progress streaming decisions)."""
    return _config.is_tty


# --- Combined mode (frontend interleaving) ---


def set_combined_mode(enabled: bool) -> None:
    """Enable or disable [deploy] prefix on backend output."""
    _config.combined_mode = enabled


def _deploy_prefix() -> str:
    """Return ``'[deploy] '`` prefix when in combined mode, else ``''``."""
    if _config.combined_mode:
        return f"{BLUE}[deploy]{RESET} "
    return ""


def _verbose_only[**P](fn: Callable[P, None]) -> Callable[P, None]:
    """Decorator that makes a function no-op when verbosity < VERBOSE."""

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        if _config.verbosity >= Verbosity.VERBOSE:
            fn(*args, **kwargs)

    return wrapper


# --- Thread-local output buffering ---


def start_buffering() -> None:
    """Enable output buffering for the current thread."""
    _config.thread_local.buffer = []  # list[tuple[str, Any]]
    _config.thread_local.buffering = True


def flush_buffer() -> list[tuple[str, Any]]:
    """Disable buffering and return accumulated ``(message, file)`` entries."""
    entries: list[tuple[str, Any]] = getattr(_config.thread_local, "buffer", [])
    _config.thread_local.buffer = []
    _config.thread_local.buffering = False
    return entries


def write_buffered_output(entries: list[tuple[str, Any]]) -> None:
    """Print all *entries* atomically under a single lock acquisition."""
    if not entries:
        return
    with _config.output_lock:
        for msg, file in entries:
            _tty_print(msg, file=file)


def _tty_print(msg: str, *, file: Any = None) -> None:
    """Print *msg* with explicit ``\\r\\n`` line endings on a TTY."""
    target = file or sys.stdout
    if _config.is_tty:
        target.write("\r")
        print(msg, end="\r\n", file=target)
    else:
        print(msg, file=target)


def _print_locked(msg: str, *, file: Any = None) -> None:
    _log_to_file(msg)
    if getattr(_config.thread_local, "buffering", False):
        _config.thread_local.buffer.append((msg, file))
        return
    with _config.output_lock:
        _tty_print(msg, file=file)


# --- Reset (for test isolation) ---


def reset() -> None:
    """Reset all output configuration to defaults. For testing."""
    global _config, _active_spinner
    if _config.log_file is not None:
        _config.log_file.close()
    _config = OutputConfig()
    _active_spinner = None
    _refresh_ansi()


# --- Global spinner access (for pausing during verbose subprocess output) ---

_active_spinner: Spinner | None = None


def set_active_spinner(spinner: Spinner) -> None:
    """Register the currently running spinner for global access."""
    global _active_spinner
    _active_spinner = spinner


def clear_active_spinner() -> None:
    """Clear the global spinner reference."""
    global _active_spinner
    _active_spinner = None


def pause_spinner() -> None:
    """Pause the active spinner so subprocess output can stream cleanly."""
    if _active_spinner is not None:
        _active_spinner.pause()


def resume_spinner() -> None:
    """Resume the active spinner after subprocess output is done."""
    if _active_spinner is not None:
        _active_spinner.resume()


class Spinner:
    """Background spinner showing active step labels on stderr.

    TTY-gated: does nothing when stderr is not a terminal (piped).
    Thread-safe via an internal lock for label management.
    """

    def __init__(self) -> None:
        self._labels: list[str] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._paused = threading.Event()
        self._paused.set()  # not paused initially
        self._thread: threading.Thread | None = None
        self._frame = 0

    def start(self) -> None:
        if not _config.is_tty:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if _config.is_tty:
            sys.stderr.write("\r\033[K")
            sys.stderr.flush()

    def add_label(self, name: str) -> None:
        with self._lock:
            if name not in self._labels:
                self._labels.append(name)

    def remove_label(self, name: str) -> None:
        with self._lock:
            if name in self._labels:
                self._labels.remove(name)

    def pause(self) -> None:
        """Pause spinner output (clear line) for clean log flushing."""
        self._paused.clear()
        # Acquire output lock to wait for any in-progress spinner write
        with _config.output_lock:
            if _config.is_tty:
                sys.stderr.write("\r\033[K")
                sys.stderr.flush()

    def resume(self) -> None:
        """Resume spinner output after log flushing."""
        self._paused.set()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            if self._paused.is_set():
                with self._lock:
                    labels = list(self._labels)
                if labels:
                    frame = _SPINNER_FRAMES[self._frame % len(_SPINNER_FRAMES)]
                    text = f"\r{frame} {', '.join(labels)}..."
                    # Truncate to terminal width if possible
                    try:
                        cols = os.get_terminal_size(sys.stderr.fileno()).columns
                        if len(text) > cols:
                            text = text[: cols - 1]
                    except (OSError, ValueError):
                        pass
                    # Hold output lock and re-check paused under lock to
                    # prevent writing after pause() has cleared the line.
                    with _config.output_lock:
                        if self._paused.is_set():
                            sys.stderr.write(f"\033[K{text}")
                            sys.stderr.flush()
                            self._frame += 1
            self._stop_event.wait(0.1)


# --- Prefixed message helpers ---


def print_blank() -> None:
    """Print a blank line (verbose-section separator)."""
    _print_locked("")


def info(msg: str) -> None:
    """Print an informational message to stdout."""
    _print_locked(f"{_deploy_prefix()}{BLUE}[info]{RESET} {msg}")


def warn(msg: str) -> None:
    """Print a warning message to stderr."""
    _print_locked(f"{_deploy_prefix()}{YELLOW}[warn]{RESET} {msg}", file=sys.stderr)


def error(msg: str) -> None:
    """Print an error message to stderr."""
    _print_locked(f"{_deploy_prefix()}{RED}[error]{RESET} {msg}", file=sys.stderr)


def success(msg: str) -> None:
    """Print a success message to stdout."""
    _print_locked(f"{_deploy_prefix()}{GREEN}[ok]{RESET} {msg}")


# --- Verbosity-gated output functions ---


def verbose(msg: str) -> None:
    """Print an [info] message only when -v or higher is active.

    Always written to the log file regardless of verbosity.
    """
    formatted = f"{_deploy_prefix()}{BLUE}[info]{RESET} {msg}"
    if _config.verbosity >= Verbosity.VERBOSE:
        _print_locked(formatted)
    else:
        # Still log to file even if not printed to console
        _log_to_file(formatted)


# --- Per-deployer one-line summary (default verbosity) ---


def print_deployer_deployed(deployer_name: str, elapsed: float, detail: str = "") -> None:
    """Print a per-deployer deployed line."""
    detail_str = f"  {DIM}({detail}){RESET}" if detail else ""
    _print_locked(
        f"{_deploy_prefix()}  {BOLD}{deployer_name:<12s}{RESET} {GREEN}{BOLD}deployed{RESET}  {DIM}{elapsed:.1f}s{RESET}{detail_str}"
    )


def print_deployer_skipped_line(deployer_name: str, reason: str) -> None:
    """Print a per-deployer skipped line."""
    _print_locked(
        f"{_deploy_prefix()}  {BOLD}{deployer_name:<12s}{RESET} {DIM}skipped   ({reason}){RESET}"
    )


def print_deploy_total(elapsed: float, *, success: bool = True) -> None:
    """Print the total deploy time. Always visible in all modes."""
    if success:
        color = GREEN
        label = "Deploy complete"
    else:
        color = RED
        label = "Deploy failed"
    _print_locked(f"\n{_deploy_prefix()}{color}{BOLD}{label}{RESET} in {elapsed:.1f}s")


# --- Targeted deploy output ---


def print_targeted_deploy_summary(
    targeted_files: tuple[str, ...],
    elapsed: float,
) -> None:
    """Print targeted deploy summary with individual file paths."""
    dp = _deploy_prefix()
    _print_locked(
        f"{dp}  {BOLD}python{' ' * 6}{RESET} {GREEN}{BOLD}deployed{RESET}  "
        f"{DIM}{elapsed:.1f}s{RESET}  {BOLD}[targeted]{RESET} {len(targeted_files)} file(s)"
    )
    for filepath in targeted_files:
        _print_locked(f"{dp}    {DIM}{filepath}{RESET}")


def print_full_deploy_indicator(elapsed: float, fallback_reason: str = "") -> None:
    """Print full deploy indicator with optional fallback reason."""
    if not fallback_reason:
        return
    dp = _deploy_prefix()
    _print_locked(
        f"{dp}  {BOLD}python{' ' * 6}{RESET} {GREEN}{BOLD}deployed{RESET}  "
        f"{DIM}{elapsed:.1f}s{RESET}  {BOLD}[full]{RESET}"
    )
    _print_locked(f"{dp}    {DIM}Fallback: {fallback_reason}{RESET}")


# --- Site info display ---


@_verbose_only
def print_site_info(site: SiteInfo) -> None:
    """Display detected site information at -v verbosity."""
    _print_locked(f"  Site:    {BOLD}{site.name}{RESET}")
    _print_locked(f"  Root:    {site.root}")
    _print_locked(f"  Edition: {site.edition.value} ({site.edition.name})")
    _print_locked(f"  Version: {site.version_string}")
    if site.build_commit is not None:
        _print_locked(f"  Commit:  {site.build_commit[:12]}")
    else:
        _print_locked(f"  Commit:  {DIM}(not available){RESET}")


# --- Change summary display ---

_CATEGORY_LABELS: MappingProxyType[ChangeCategory, str] = MappingProxyType(
    {
        ChangeCategory.PYTHON: "Python",
        ChangeCategory.CPP: "C++",
        ChangeCategory.RUST: "Rust",
        ChangeCategory.VUE: "Vue/TypeScript",
        ChangeCategory.FRONTEND: "Frontend (legacy)",
        ChangeCategory.CONFIG: "Config/Scripts",
        ChangeCategory.DATA: "Data/Locale",
        ChangeCategory.BUILD: "Build System",
        ChangeCategory.TEST: "Tests",
        ChangeCategory.OTHER: "Other",
    }
)


@_verbose_only
def print_change_summary(changes: ChangeSet) -> None:
    """Display a categorized summary of detected changes."""
    info(f"Changes detected: {len(changes.files)} file(s)")
    _print_locked(f"  Base commit: {changes.build_commit[:12]}")

    for category in ChangeCategory:
        files = changes.categories.get(category)
        if files:
            label = _CATEGORY_LABELS[category]
            _print_locked(f"  {label}: {len(files)} file(s)")

    if changes.has_python_only:
        _print_locked(f"  {DIM}Fast path eligible (Python only){RESET}")


# --- Deploy state display ---


def print_all_skipped() -> None:
    """Print the clean exit message when all deployers are skipped."""
    success("All deployers up to date, nothing to deploy")


@_verbose_only
def print_fallback_note(deployer_name: str) -> None:
    """Print a note when a deployer falls back to global HEAD check."""
    _print_locked(f"  {DIM}{deployer_name}: using global check (no source paths){RESET}")


def print_restart_skipped() -> None:
    """Print message when service restart is skipped due to no deployed targets needing it."""
    info("Service restart skipped: no deployed targets require apache/cmk restart")


@_verbose_only
def print_state_info(diff_base_source: str, diff_base_commit: str) -> None:
    """Display the source of the diff base being used."""
    if diff_base_source == "state":
        _print_locked(f"  {DIM}Diff base: last deploy ({diff_base_commit[:12]}){RESET}")
    else:
        _print_locked(f"  {DIM}Diff base: site build ({diff_base_commit[:12]}){RESET}")


# --- Bazel target summary display ---


@_verbose_only
def print_target_summary(targets: BazelTargetSet) -> None:
    """Display resolved Bazel targets."""

    if targets.is_empty and targets.files_queried == 0:
        return

    if targets.is_empty and targets.files_queried > 0:
        info("No Bazel targets affected")
        return

    info(f"Bazel targets: {len(targets.targets)} target(s)")
    if targets.from_cache:
        _print_locked(f"  {DIM}(cached query){RESET}")
    else:
        _print_locked(f"  {DIM}(query: {targets.query_time_ms}ms){RESET}")

    for target in sorted(targets.targets, key=lambda t: t.label):
        _print_locked(f"  {target.kind.value}  {target.label}")


@_verbose_only
def print_build_path(build_path: str) -> None:
    """Display the chosen deployment strategy (fast/full)."""
    if build_path == "fast":
        _print_locked(f"{DIM}Build path: Python fast path (skip Bazel){RESET}")
    elif build_path == "full":
        info("Build path: Bazel build required")


# --- Build result display ---


@_verbose_only
def print_build_result(result: BuildResult) -> None:
    """Display Bazel build and install results."""
    success(f"Bazel build complete in {result.elapsed:.1f}s")
    _print_locked(f"  Targets built: {result.targets_built}")
    _print_locked(f"  Artifacts installed: {result.artifacts_installed}")
    if result.skipped_edition > 0:
        info(f"Skipped {result.skipped_edition} spec(s) not matching site edition")


@_verbose_only
def print_config_result(result: ConfigDeployResult) -> None:
    """Display config/data deployment results."""
    success(f"Config deployment complete in {result.elapsed:.1f}s")
    _print_locked(f"  Specs deployed: {result.specs_deployed}")
    if result.files_installed > 0:
        _print_locked(f"  Files installed: {result.files_installed}")
    if result.locale_compiled > 0:
        _print_locked(f"  Locale files compiled: {result.locale_compiled}")


@_verbose_only
def print_wheel_result(result: WheelDeployResult) -> None:
    """Display wheel deployment results."""
    success(f"Wheel deployment complete in {result.elapsed:.1f}s")
    _print_locked(f"  Packages deployed: {result.wheels_deployed}")
    if result.wheels_skipped > 0:
        _print_locked(f"  Packages skipped: {result.wheels_skipped} (unchanged)")
    if result.wheels_skipped_edition > 0:
        info(f"Skipped {result.wheels_skipped_edition} spec(s) not matching site edition")
    if result.wheels_skipped_missing > 0:
        info(f"Skipped {result.wheels_skipped_missing} spec(s) with missing source dirs")


# --- Service management display ---


def print_service_preview(
    services: list[tuple[Service, ServiceAction]],
    *,
    no_restart: bool,
) -> None:
    """Display which services will be restarted/reloaded.

    Args:
        services: Dependency-ordered list of ``(Service, ServiceAction)`` pairs.
        no_restart: True when ``--no-restart`` flag is set (skip execution).
    """
    if no_restart:
        info(f"Services affected (skipped due to --no-restart): {len(services)}")
    else:
        info(f"Restarting {len(services)} service(s):")
    for svc, action in services:
        _print_locked(f"  {action.value:8s} {svc.value}")


def print_service_result(result: ServiceResult) -> None:
    """Display the outcome of service restart/reload operations."""
    if result.services_failed == 0:
        success(f"Service restarts complete in {result.elapsed:.1f}s")
    else:
        warn(
            f"Service restarts complete in {result.elapsed:.1f}s ({result.services_failed} failed)"
        )
        for name in result.failures:
            _print_locked(f"  {YELLOW}failed{RESET}  {name}")
        _print_locked(f"  {DIM}Run 'omd restart <service>' manually to retry{RESET}")
    _print_locked(f"  Services restarted: {result.services_restarted}")


# --- Parallel execution display ---


@_verbose_only
def print_parallel_result(results: list[StepResult]) -> None:
    """Display results of parallel deployment execution."""

    succeeded = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    if succeeded:
        for r in succeeded:
            msg = f" -- {r.message}" if r.message else ""
            _print_locked(
                f"  {GREEN}ok{RESET}    {r.name:<25s} {DIM}({r.elapsed:.1f}s){RESET}{msg}"
            )

    if failed:
        for r in failed:
            msg = f" -- {r.message}" if r.message else ""
            _print_locked(f"  {RED}fail{RESET}  {r.name:<25s}{msg}")


# --- Dry-run display ---


def print_dry_run_plan(
    build_path: str,
    changes: ChangeSet | None,
    targets: BazelTargetSet | None,
    services: list[tuple[Service, ServiceAction]],
    expanded_deps: set[str] | None,
) -> None:
    """Display a complete deployment plan without executing anything."""
    _print_locked(f"\n{BOLD}DRY RUN -- no changes will be made{RESET}")

    if expanded_deps:
        _print_locked("\n  Transitive dependencies would also be deployed:")
        for dep in sorted(expanded_deps):
            _print_locked(f"    {dep}")

    if build_path == "fast":
        _print_locked("\n  Would deploy: Python files (fast path)")
    else:
        _print_locked("\n  Would deploy: Python files + Bazel targets")

    if build_path == "full" and targets is not None and not targets.is_empty:
        for target in sorted(targets.targets, key=lambda t: t.label):
            _print_locked(f"    build  {target.label}")

    if changes is None or (
        ChangeCategory.CONFIG in changes.categories or ChangeCategory.DATA in changes.categories
    ):
        _print_locked("  Would deploy: config/data files")

    if changes is None:
        _print_locked("  Would deploy: wheel packages (full)")

    if services:
        _print_locked("")
        print_service_preview(services, no_restart=True)

    _print_locked("")
    success("Dry run complete. No files were modified.")


# --- Verbose change listing ---


@_verbose_only
def print_verbose_changes(
    changes: ChangeSet,
    *,
    frontend_supervised: bool = False,
) -> None:
    """Display a per-file listing of all detected changes."""
    _fs_prefixes: frozenset[str]
    if frontend_supervised:
        from cmk.dev_deploy.manifest.reader import get_frontend_supervised_prefixes

        _fs_prefixes = get_frontend_supervised_prefixes()
    else:
        _fs_prefixes = frozenset()
    for category in ChangeCategory:
        files = changes.categories.get(category)
        if files:
            label = _CATEGORY_LABELS[category]
            _print_locked(f"  {label}:")
            for filepath in files:
                if _fs_prefixes and any(filepath.startswith(p) for p in _fs_prefixes):
                    _print_locked(f"    {filepath} {DIM}(Vite HMR){RESET}")
                else:
                    _print_locked(f"    {filepath}")


# --- Frontend supervisor output ---


def print_frontend_hint(changes: ChangeSet) -> None:
    """Print a hint suggesting --frontend when Vue files are present."""
    vue_files = changes.categories.get(ChangeCategory.VUE, ())
    if not vue_files:
        return
    from cmk.dev_deploy.manifest.reader import get_frontend_supervised_prefixes

    prefixes = get_frontend_supervised_prefixes()
    if any(f.startswith(p) for f in vue_files for p in prefixes):
        _print_locked(f"  {DIM}Tip: use --frontend for subsecond Vue feedback via Vite HMR{RESET}")


def print_frontend_skip(package_name: str) -> None:
    """Print the skipped-by-Vite line for a frontend-supervised package.

    Args:
        package_name: Human-friendly package name, e.g. ``'cmk-frontend-vue'``.
    """
    print_deployer_skipped_line(package_name, "skipped (handled by Vite)")


# --- Dependency expansion display ---


@_verbose_only
def print_dep_expansion(expanded: set[str], original: set[str]) -> None:
    """Display additional directories added via dependency expansion."""
    new_deps = expanded - original
    if not new_deps:
        return
    info(f"Dependency expansion: {len(new_deps)} additional dir(s) will be deployed")
    for dep in sorted(new_deps):
        _print_locked(f"    {dep}")


# --- Debug-level output (skip traces and state) ---

# --- Watch mode display ---


def print_watch_waiting(site_name: str) -> None:
    """Display watch mode waiting message."""
    _print_locked(f"\n{BOLD}Watching for changes...{RESET} (site: {site_name}, Ctrl-C to stop)")


def print_watch_cycle_header(cycle: int) -> None:
    """Display watch mode cycle start header."""
    import datetime

    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    dp = _deploy_prefix()
    separator = "\u2500" * 60 if _config.use_color else "-" * 60
    _print_locked(f"\n{dp}{DIM}{separator}{RESET}")
    _print_locked(f"{dp}{BOLD}[{timestamp}] Deploy cycle #{cycle}{RESET}")


def print_watch_cycle_complete(cycle: int, exit_code: int, elapsed: float) -> None:
    """Display watch mode cycle completion."""
    if exit_code == 0:
        success(f"Cycle #{cycle} complete in {elapsed:.1f}s")
    else:
        warn(f"Cycle #{cycle} failed (exit code {exit_code}) in {elapsed:.1f}s")


def print_watch_cycle_summary(cycle: int, result: DeployCycleResult, elapsed: float) -> None:
    """Display a one-line watch cycle summary with deployed/skipped deployers."""
    parts: list[str] = []
    if result.deployed:
        parts.append(f"deployed {', '.join(result.deployed)}")
    if result.skipped:
        count = len(result.skipped)
        items = ", ".join(result.skipped)
        parts.append(f"skipped {count} ({items})")
    detail = " -- ".join(parts) if parts else "complete"
    success(f"Cycle #{cycle} in {elapsed:.1f}s: {detail}")


def print_watch_all_skipped(cycle: int, elapsed: float) -> None:
    """Display a dim one-liner when all deployers were skipped."""
    _print_locked(f"{_deploy_prefix()}  {DIM}Cycle #{cycle}: all skipped ({elapsed:.1f}s){RESET}")


@_verbose_only
def print_watch_cycle_verbose(result: DeployCycleResult) -> None:
    """Display per-deployer deployed/skipped lines with skip reasons."""
    dp = _deploy_prefix()
    for name in result.deployed:
        _print_locked(f"{dp}  {GREEN}deployed{RESET}: {name}")
    for name in result.skipped:
        reason = result.skipped_reasons.get(name, "")
        reason_str = f" ({reason})" if reason else ""
        _print_locked(f"{dp}  {DIM}skipped: {name}{reason_str}{RESET}")


def print_watch_services_restarted(count: int) -> None:
    """Display the count of services restarted after a watch cycle."""
    info(f"Services restarted: {count}")


def print_watch_resume() -> None:
    """Display the resume message after a watch cycle completes."""
    _print_locked(f"{DIM}Watching for changes... (Ctrl-C to stop){RESET}")


def print_watch_heartbeat(idle_polls: int) -> None:
    """Display dim heartbeat to confirm watcher is alive during idle polling."""
    minutes = idle_polls // 60
    _print_locked(f"{_deploy_prefix()}{DIM}  ... still watching ({minutes}m idle){RESET}")


# --- Batched targeted deploy summary (consolidates per-spec output) ---


def print_targeted_deploy_batch(
    results: list[tuple[str, tuple[str, ...], float]],
) -> None:
    """Print consolidated targeted deploy summary, one line per unique package."""
    if not results:
        return
    dp = _deploy_prefix()
    for pkg_name, files, elapsed in results:
        _print_locked(
            f"{dp}  {BOLD}python{' ' * 6}{RESET} {GREEN}{BOLD}deployed{RESET}  "
            f"{DIM}{elapsed:.1f}s{RESET}  {BOLD}[targeted]{RESET} {pkg_name} ({len(files)} file(s))"
        )
        if _config.verbosity >= Verbosity.VERBOSE:
            for filepath in files:
                _print_locked(f"{dp}    {DIM}{filepath}{RESET}")


def print_wheel_full_deploy(package_name: str, elapsed: float) -> None:
    """Print a per-package line for full (non-targeted) wheel deploys."""
    dp = _deploy_prefix()
    _print_locked(
        f"{dp}  {BOLD}python{' ' * 6}{RESET} {GREEN}{BOLD}deployed{RESET}  "
        f"{DIM}{elapsed:.1f}s{RESET}  [full] {package_name}"
    )


# --- Parallel execution timeline (ASCII Gantt chart) ---


@_verbose_only
def print_parallel_timeline(
    results: list[StepResult],
    total_elapsed: float,
    manifest_elapsed: float = 0.0,
    overlay_elapsed: float = 0.0,
    services_elapsed: float = 0.0,
) -> None:
    """Print an ASCII Gantt chart of parallel step execution."""

    # Build entries: (name, start, end)
    # Manifest runs first, then overlay (sequential).
    entries: list[tuple[str, float, float]] = []
    pre_offset = 0.0
    if manifest_elapsed > 0:
        entries.append(("manifest", 0.0, manifest_elapsed))
        pre_offset = manifest_elapsed
    if overlay_elapsed > 0:
        entries.append(("overlay", pre_offset, pre_offset + overlay_elapsed))
        pre_offset += overlay_elapsed

    # Deployers run in parallel after pre-steps.
    post_deployer_end = pre_offset
    for r in results:
        if not r.success:
            continue
        start = pre_offset + r.start_offset
        end = start + r.elapsed
        entries.append((r.name, start, end))
        post_deployer_end = max(post_deployer_end, end)

    # Services run sequentially after all deployers complete.
    if services_elapsed > 0:
        entries.append(("services", post_deployer_end, post_deployer_end + services_elapsed))

    if not entries:
        return

    # Determine display names
    from cmk.dev_deploy.execution.step_registry import STEP_DISPLAY_NAMES as _display

    dp = _deploy_prefix()
    width = 40
    span = total_elapsed if total_elapsed > 0 else 1.0

    _print_locked(f"\n{dp}  {BOLD}Timeline ({total_elapsed:.1f}s):{RESET}")
    for name, start, end in entries:
        display = _display.get(name, name)
        elapsed = end - start
        pct = int(elapsed / span * 100) if span > 0 else 0
        col_start = int(start / span * width)
        col_end = max(col_start + 1, int(end / span * width))
        bar = "░" * col_start + "█" * (col_end - col_start) + "░" * (width - col_end)
        _print_locked(f"{dp}  {display:<10s} {bar}  {DIM}{start:.1f}-{end:.1f}s ({pct}%){RESET}")
