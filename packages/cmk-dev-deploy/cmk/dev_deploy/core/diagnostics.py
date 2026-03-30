# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Automatic diagnostic bundle capture for cmk-dev-deploy.

On any :class:`~cmk.dev_deploy.errors.DeployError` (or subclass), captures
a structured JSON file with environment info, Bazel state, manifest state,
deploy state, and the tail of the deploy log.  Developers share this file
with the tool maintainer instead of describing what happened.

Storage: ``~/.cmk-dev-deploy/diagnostics/`` — outside the OverlayFS area
so bundles survive ``--purge`` and ``--full`` operations.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import traceback
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, TYPE_CHECKING

from cmk.dev_deploy.core.timeouts import BAZEL_INFO_QUICK
from cmk.dev_deploy.errors import DeployError

if TYPE_CHECKING:
    from cmk.dev_deploy.types import SiteInfo


def _diagnostics_dir() -> Path:
    return Path.home() / ".cmk-dev-deploy" / "diagnostics"


_MAX_CRASH_FILES = 20
_LOG_TAIL_LINES = 200


def capture_diagnostic_bundle(
    error: BaseException,
    *,
    site: SiteInfo | None = None,
    repo_root: Path | None = None,
    phase: str = "unknown",
    json_errors: bool = False,
) -> Path | None:
    """Capture a diagnostic bundle for the given error.

    This function is deliberately defensive — every sub-collector can fail
    independently without crashing the bundle.  A partial bundle is always
    better than no bundle.

    Args:
        error: The exception that triggered the diagnostic capture.
        site: Resolved site info, if available.
        repo_root: Repository root, if available.
        phase: Deploy phase where the error occurred (e.g. "manifest_build").
        json_errors: If True, also print the bundle as JSON to stdout.

    Returns:
        Path to the written crash file, or None if writing failed.
    """
    bundle: dict[str, Any] = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "tool_version": _get_tool_version(),
        "command_args": sys.argv[1:],
    }

    bundle["environment"] = _collect_environment(repo_root)
    bundle["bazel_state"] = _collect_bazel_state(repo_root)

    if site is not None:
        bundle["site_info"] = _collect_site_info(site)

    bundle["manifest_state"] = _collect_manifest_state()
    bundle["deploy_state"] = _collect_deploy_state(site)
    bundle["error"] = _collect_error_info(error, phase)
    bundle["logs"] = _read_log_tail()

    # Write to disk
    crash_path = _write_bundle(bundle)

    # Print human-readable error output to stderr
    _print_error_output(error, crash_path)

    # Optionally print JSON to stdout (for --json-errors)
    if json_errors:
        try:
            print(json.dumps(bundle, indent=2, default=str))  # noqa: T201
        except OSError:
            pass  # stdout closed

    return crash_path


# ---------------------------------------------------------------------------
# Sub-collectors (each handles its own errors)
# ---------------------------------------------------------------------------


def _get_tool_version() -> str:
    """Detect tool version via importlib.metadata, git describe, or 'unknown'."""
    try:
        from importlib.metadata import version

        return version("cmk-dev-deploy")
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty"],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return "unknown"


def _collect_environment(repo_root: Path | None) -> dict[str, Any]:
    """Collect environment info without capturing env vars."""
    env: dict[str, Any] = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
    }

    # Bazel version
    try:
        result = subprocess.run(
            ["bazel", "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=BAZEL_INFO_QUICK,
        )
        if result.returncode == 0:
            env["bazel_version"] = result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        env["bazel_version"] = "unavailable"

    # Git info
    if repo_root is not None:
        try:
            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
                cwd=str(repo_root),
                timeout=3,
            )
            if branch.returncode == 0:
                env["git_branch"] = branch.stdout.strip()

            commit = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
                cwd=str(repo_root),
                timeout=3,
            )
            if commit.returncode == 0:
                env["git_commit"] = commit.stdout.strip()

            dirty = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                check=False,
                cwd=str(repo_root),
                timeout=5,
            )
            if dirty.returncode == 0:
                env["git_dirty_count"] = len(
                    [line for line in dirty.stdout.strip().splitlines() if line]
                )
        except (subprocess.TimeoutExpired, OSError):
            pass

    return env


def _collect_bazel_state(repo_root: Path | None) -> dict[str, Any]:
    """Collect Bazel server state (PID, memory) with timeouts."""
    state: dict[str, Any] = {}
    if repo_root is None:
        return state

    cwd = str(repo_root)

    # Get output_base
    try:
        result = subprocess.run(
            ["bazel", "info", "output_base"],
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
            timeout=BAZEL_INFO_QUICK,
        )
        if result.returncode == 0:
            ob = result.stdout.strip()
            state["output_base"] = ob
            state["output_base_exists"] = Path(ob).is_dir()
    except (subprocess.TimeoutExpired, OSError):
        state["output_base"] = "unavailable (bazel info timed out)"

    # Get execution root
    try:
        result = subprocess.run(
            ["bazel", "info", "execution_root"],
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
            timeout=BAZEL_INFO_QUICK,
        )
        if result.returncode == 0:
            state["execution_root_exists"] = Path(result.stdout.strip()).is_dir()
    except (subprocess.TimeoutExpired, OSError):
        pass

    # Check bazel-bin exists
    state["bazel_bin_exists"] = (repo_root / "bazel-bin").exists()

    # Bazel server PID + memory
    try:
        result = subprocess.run(
            ["bazel", "info", "server_pid"],
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
            timeout=BAZEL_INFO_QUICK,
        )
        if result.returncode == 0:
            pid_str = result.stdout.strip()
            state["server_pid"] = int(pid_str)

            # Read VmRSS from /proc/<pid>/status (Linux only)
            try:
                proc_status = Path(f"/proc/{pid_str}/status")
                if proc_status.is_file():
                    for line in proc_status.read_text().splitlines():
                        if line.startswith("VmRSS:"):
                            state["server_memory_kb"] = int(line.split()[1])
                            break
            except (OSError, ValueError, IndexError):
                pass
    except (subprocess.TimeoutExpired, OSError, ValueError):
        pass

    return state


def _collect_site_info(site: SiteInfo) -> dict[str, Any]:
    """Collect site information."""
    from cmk.dev_deploy.site.overlay import is_overlay_active

    info: dict[str, Any] = {
        "site_name": site.name,
        "edition": site.edition.value,
    }
    try:
        info["overlay_mounted"] = is_overlay_active(site.root)
    except Exception:
        info["overlay_mounted"] = "unknown"
    return info


def _collect_manifest_state() -> dict[str, Any]:
    """Collect manifest state metadata."""
    from cmk.dev_deploy.manifest.reader import manifest_path

    state: dict[str, Any] = {"manifest_exists": manifest_path().is_file()}
    if manifest_path().is_file():
        try:
            stat = manifest_path().stat()
            import time

            state["manifest_age_seconds"] = int(time.time() - stat.st_mtime)
            data = json.loads(manifest_path().read_text())
            if isinstance(data, dict):
                state["manifest_spec_count"] = {
                    k: len(v) for k, v in data.items() if isinstance(v, list)
                }
        except (OSError, json.JSONDecodeError):
            pass
    return state


def _collect_deploy_state(site: SiteInfo | None) -> dict[str, Any]:
    """Collect deploy state metadata."""
    if site is None:
        return {}
    try:
        from cmk.dev_deploy.state.deploy_state import load_state

        state = load_state(site.root)
        if state is None:
            return {"state_file_exists": False}
        return {
            "state_file_exists": True,
            "schema_version": 2,
            "deployer_count": len(state.deployers),
            "diff_base_commit": state.diff_base_commit,
            "branch_in_state": state.branch,
        }
    except Exception:
        return {"state_file_exists": "error"}


def _collect_error_info(error: BaseException, phase: str) -> dict[str, Any]:
    """Collect error details."""
    info: dict[str, Any] = {
        "type": type(error).__name__,
        "message": str(error.message) if isinstance(error, DeployError) else str(error),
        "traceback": traceback.format_exception(type(error), error, error.__traceback__),
        "phase": phase,
    }
    if isinstance(error, DeployError) and error.recovery:
        info["recovery_hint"] = error.recovery
    return info


def _read_log_tail() -> str | None:
    """Read the last N lines of the current deploy log file."""
    from cmk.dev_deploy.core.output import get_log_file_path

    log_path = get_log_file_path()
    if log_path is None or not log_path.is_file():
        return None
    try:
        lines = log_path.read_text().splitlines()
        return "\n".join(lines[-_LOG_TAIL_LINES:])
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Bundle writing and pruning
# ---------------------------------------------------------------------------


def _write_bundle(bundle: dict[str, Any]) -> Path | None:
    """Write the diagnostic bundle to disk and prune old files."""
    try:
        _diagnostics_dir().mkdir(parents=True, exist_ok=True)
    except OSError:
        _print_write_warning()
        return None

    ts = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
    crash_path = _diagnostics_dir() / f"crash-{ts}.json"

    try:
        crash_path.write_text(json.dumps(bundle, indent=2, default=str) + "\n")
    except OSError:
        _print_write_warning()
        return None

    # Prune old crash files (keep max _MAX_CRASH_FILES)
    try:
        crash_files = sorted(_diagnostics_dir().glob("crash-*.json"), key=lambda p: p.name)
        for old in crash_files[:-_MAX_CRASH_FILES]:
            old.unlink(missing_ok=True)
    except OSError:
        pass  # Pruning failure is non-critical

    return crash_path


def _print_write_warning() -> None:
    """Warn that the diagnostic bundle could not be saved."""
    print(  # noqa: T201
        f"WARNING: Could not save diagnostic bundle to {_diagnostics_dir()}",
        file=sys.stderr,
    )


def _print_error_output(error: BaseException, crash_path: Path | None) -> None:
    """Print human-readable error output with recovery hints to stderr."""
    msg = str(error)
    print(f"\nERROR: {msg}", file=sys.stderr)  # noqa: T201

    if crash_path is not None:
        print(  # noqa: T201
            f"\n  Diagnostic bundle saved to:\n"
            f"    {crash_path}\n\n"
            f"  Share it with the tool maintainer:\n"
            f"    cat {crash_path} | xclip -selection clipboard",
            file=sys.stderr,
        )
