# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared subprocess runner with unified timeout and error handling."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from cmk.dev_deploy.errors import DeployError


def run_checked(
    cmd: Sequence[str],
    *,
    cwd: Path | str,
    timeout: int,
    error_cls: type[Exception] = DeployError,
    description: str = "",
    recovery: str = "",
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess, raising on timeout, OS error, or non-zero exit.

    Returns the CompletedProcess on success. On failure, raises *error_cls*
    with a formatted message including exit code and stderr.
    """
    desc = description or cmd[0]
    try:
        result = subprocess.run(
            list(cmd),
            capture_output=True,
            text=True,
            check=False,
            cwd=str(cwd),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        _raise(error_cls, f"{desc} timed out after {timeout}s", recovery)
    except OSError as exc:
        _raise(error_cls, f"{desc} failed: {exc}", recovery, cause=exc)

    if result.returncode != 0:
        stderr = result.stderr.strip()
        msg = f"{desc} failed (exit {result.returncode})"
        if stderr:
            msg = f"{msg}: {stderr}"
        _raise(error_cls, msg, recovery)

    return result


def _raise(
    error_cls: type[Exception],
    msg: str,
    recovery: str,
    cause: BaseException | None = None,
) -> NoReturn:
    """Raise *error_cls* with recovery hint when supported."""
    if issubclass(error_cls, DeployError) and recovery:
        raise error_cls(msg, recovery=recovery) from cause
    raise error_cls(msg) from cause
