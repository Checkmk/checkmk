# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Root privilege helpers for cmk-dev-deploy.

Root is needed in exactly two places: the one-time sudoers bootstrap
(:mod:`sudoers`) and applying file capabilities to freshly deployed
binaries (:func:`try_setcap`).  Commands that run as the **site user**
go through :func:`cmk.dev_deploy.site.sudoers.run_as_site_user` instead.
"""

import getpass
import os
import subprocess
from pathlib import Path

from cmk.dev_deploy.core import output


def get_real_user() -> str:
    """Return the actual human user, even when running under ``sudo``.

    Checks ``SUDO_USER`` first (set by sudo), then falls back to
    ``getpass.getuser()``.
    """
    return os.environ.get("SUDO_USER") or getpass.getuser()


def ensure_sudo() -> None:
    """Pre-authenticate sudo so subsequent calls don't prompt.

    Runs ``sudo -v`` with a custom prompt, allowing the user to enter
    their password on the terminal.  The sudo timestamp is then cached
    for subsequent ``run_as_root`` calls (which use capture_output).
    """
    if os.geteuid() == 0:
        return
    # Unset SUDO_ASKPASS so sudo prompts on the terminal directly
    env = {k: v for k, v in os.environ.items() if k != "SUDO_ASKPASS"}
    subprocess.run(
        ["sudo", "-v", "-p", "[cmk-dev-deploy] sudo password for %u: "],
        check=False,
        env=env,
    )


def run_as_root(
    cmd: list[str],
    **kwargs: object,
) -> subprocess.CompletedProcess[str]:
    """Run a command with root privileges via ``sudo``.

    If already running as root, skips the ``sudo`` prefix.
    Assumes :func:`ensure_sudo` was called earlier so the sudo
    timestamp is cached and no interactive prompt is needed.
    """
    full_cmd = cmd if os.geteuid() == 0 else ["sudo", "-n", *cmd]
    result: subprocess.CompletedProcess[str] = subprocess.run(  # type: ignore[call-overload]
        full_cmd,
        capture_output=True,
        text=True,
        check=False,
        **kwargs,
    )
    return result


def try_setcap(path: Path, cap: str) -> bool:
    """Apply file capabilities via ``setcap``.

    Tries without sudo first (works if the user has CAP_SETFCAP or is
    root).  If that fails, calls :func:`ensure_sudo` to prompt for
    credentials and retries via :func:`run_as_root`.

    Returns:
        True if the capability was set, False on failure.
    """
    # Try without sudo (works if running as root or has capability)
    result = subprocess.run(
        ["setcap", cap, str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        output.verbose(f"  setcap {cap} {path.name}")
        return True

    # Need sudo — ensure credentials are cached first
    output.info(f"Setting capabilities on {path.name} requires sudo")
    ensure_sudo()
    result = run_as_root(["setcap", cap, str(path)])
    if result.returncode == 0:
        output.verbose(f"  setcap {cap} {path.name} (via sudo)")
        return True

    output.error(
        f"Failed to set capabilities on {path.name} ({cap}): "
        f"{result.stderr.strip() or 'unknown error'}"
    )
    output.info(f"  Manual fix: sudo setcap {cap} {path}")
    return False
