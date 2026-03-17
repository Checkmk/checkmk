# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Pre-flight Bazel environment validation.

Runs fast checks before any ``bazel query`` or ``bazel cquery`` to catch
common environment issues (stale outputs, broken installation, full disk)
before they cascade into cryptic query failures.

Each check returns a :class:`PreflightWarning`.  Warnings with
``blocking=True`` should cause the tool to error out immediately.
Non-blocking warnings are informational.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from cmk.dev_deploy.core.timeouts import BAZEL_INFO_QUICK


@dataclass(frozen=True)
class PreflightWarning:
    """A single pre-flight check result."""

    message: str
    detail: str = ""
    recovery: str = ""
    blocking: bool = False


def preflight_bazel_check(repo_root: Path) -> list[PreflightWarning]:
    """Run fast Bazel environment checks (<5s total).

    Catches common issues before they cascade into cryptic query failures.
    If ``bazel info`` times out (cold server startup), remaining pre-flight
    checks are skipped — the query phase will start the server anyway.

    Args:
        repo_root: Absolute path to the git repository root.

    Returns:
        List of warnings.  Callers should error out on any with ``blocking=True``.
    """
    warnings: list[PreflightWarning] = []

    # Check bazel info succeeds (catches broken installations).
    # Uses a short timeout.  Two failure modes:
    # - Timeout (cold server startup): NON-BLOCKING, skip remaining checks
    # - Error (broken install, permission denied): BLOCKING
    info_result = _bazel_info_check(repo_root)
    if info_result == "timeout":
        # Cold server — skip remaining pre-flight, query phase will start it
        return warnings
    if info_result == "error":
        warnings.append(
            PreflightWarning(
                message="Bazel installation appears broken",
                recovery="Check your Bazel installation and PATH",
                blocking=True,
            )
        )
        return warnings

    # 3. Check output_base is accessible and not on a full disk.
    health = _output_base_healthy(repo_root)
    if health is not None:
        warnings.append(
            PreflightWarning(
                message="Bazel output base may be corrupted or disk full",
                detail=health,
                recovery="Run: bazel clean --expunge",
            )
        )

    return warnings


def _bazel_info_check(repo_root: Path) -> str:
    """Run ``bazel info`` with a short timeout.

    Returns:
        ``"ok"`` if bazel info succeeded,
        ``"timeout"`` if it timed out (cold server),
        ``"error"`` if it failed with a non-timeout error.
    """
    try:
        result = subprocess.run(
            ["bazel", "info"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(repo_root),
            timeout=BAZEL_INFO_QUICK,
        )
    except subprocess.TimeoutExpired:
        return "timeout"
    except OSError:
        return "error"
    return "ok" if result.returncode == 0 else "error"


def _output_base_healthy(repo_root: Path) -> str | None:
    """Check that the Bazel output base is accessible.

    Returns None if healthy, or a description of the problem.
    """
    try:
        result = subprocess.run(
            ["bazel", "info", "output_base"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(repo_root),
            timeout=BAZEL_INFO_QUICK,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None  # Already caught by _bazel_info_check; skip here

    if result.returncode != 0:
        return f"bazel info output_base failed: {result.stderr.strip()[:200]}"

    output_base = Path(result.stdout.strip())
    if not output_base.is_dir():
        return f"Output base directory does not exist: {output_base}"

    # Check disk space (basic: can we create a temp file?)
    try:
        test_file = output_base / ".cmk-dev-deploy-health-check"
        test_file.write_text("ok")
        test_file.unlink()
    except OSError as e:
        return f"Output base not writable: {e}"

    return None
