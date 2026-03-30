# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Side-channel ``.mk`` file management for frontend inject mode.

Manages a side-channel override file (``zzz_dev_inject.mk``) in the site's
``multisite.d/`` directory that sets ``load_frontend_vue = "inject"``.  This
eliminates the manual GUI step of toggling the setting when developing frontend
components with ``--frontend``.

The ``.mk`` file is loaded by Checkmk's GUI config pipeline on every HTTP
request (``cmk/gui/config.py:load_config()``), meaning no Apache reload is
needed -- the change takes effect on the next browser request.  The ``zzz_``
prefix ensures the file sorts after ``wato/global.mk``, making it a clean
override.

Lifecycle:
    1. Write ``.mk`` AFTER Vite is confirmed ready (no race condition)
    2. Remove ``.mk`` on shutdown (Ctrl-C, clean exit, or crash recovery)
    3. Detect stale ``.mk`` files from previous crashes via PID file
"""

from __future__ import annotations

import os
from pathlib import Path

from cmk.dev_deploy.site.privilege import run_as_site_user, SSHState

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MK_CONTENT = """\
# Managed by cmk-dev-deploy --frontend
# This file is automatically created and removed. Do not edit manually.
load_frontend_vue = "inject"
"""
"""Content of the side-channel ``.mk`` override file.

This is valid Python executed by ``exec()`` in Checkmk's config loader.
The ``"inject"`` value tells the GUI to load frontend assets from the
Vite dev server instead of static files.
"""

_OVERRIDE_FILENAME = "zzz_dev_inject.mk"
"""Filename for the side-channel override.

The ``zzz_`` prefix ensures this file sorts AFTER ``wato/global.mk``
(because ``z`` > ``w`` in lexicographic order), so the override wins
when Checkmk's config loader processes files in sorted path order.
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def override_mk_path(site_root: Path) -> Path:
    """Return the path for the dev-deploy side-channel ``.mk`` file.

    Args:
        site_root: Absolute path to the OMD site root, e.g.
            ``Path('/omd/sites/v260')``.

    Returns:
        Absolute path to the override file, e.g.
        ``/omd/sites/v260/etc/check_mk/multisite.d/zzz_dev_inject.mk``.
    """
    return site_root / "etc" / "check_mk" / "multisite.d" / _OVERRIDE_FILENAME


def check_site_running(site_name: str, state: SSHState) -> bool:
    """Return True if the OMD site is running (all services up).

    Uses :func:`~cmk.dev_deploy.privilege.run_as_site_user` which tries
    SSH first and falls back to ``sudo --login -u``.  Returns True when
    the exit code is 0 (all services healthy).

    Args:
        site_name: OMD site name, e.g. ``'v260'``.

    Returns:
        True if the site is running, False otherwise (including timeout).
    """
    try:
        result = run_as_site_user(site_name, "omd status", state, timeout=10)
        return result.returncode == 0
    except Exception:
        return False


def _mk_file_exists(mk_path: Path, site_name: str, state: SSHState) -> bool:
    """Check if the ``.mk`` override file exists, with site-user fallback.

    Direct stat may fail with ``PermissionError`` when the site's
    ``etc/check_mk/`` directory is mode 750 and the deploy user is not
    the site user.  Falls back to ``test -f`` via :func:`run_as_site_user`.
    """
    try:
        return mk_path.exists()
    except PermissionError:
        pass
    try:
        result = run_as_site_user(site_name, f"test -f {mk_path}", state, timeout=10)
        return result.returncode == 0
    except Exception:
        return False


def is_stale_override(mk_path: Path, pid_file: Path, site_name: str, state: SSHState) -> bool:
    """Return True if the ``.mk`` override file exists but the frontend process is dead.

    Uses the PID file for liveness detection:

    - No ``.mk`` file exists: not stale (nothing to clean up)
    - ``.mk`` exists but no PID file: stale (override with no process)
    - ``.mk`` exists and PID is alive: not stale (another instance running)
    - ``.mk`` exists and PID is dead/invalid: stale (crash recovery needed)

    Args:
        mk_path: Path to the override ``.mk`` file.
        pid_file: Path to the iBazel PID file.
        site_name: OMD site name, e.g. ``'v260'``.
        state: SSH state for privilege escalation.

    Returns:
        True if the override file is stale and should be cleaned up.
    """
    if not _mk_file_exists(mk_path, site_name, state):
        return False  # No override file, nothing is stale

    if not pid_file.exists():
        return True  # Override exists but no PID file -> stale

    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)  # Check if process is alive (signal 0 = no-op probe)
        return False  # Process alive -> not stale (another instance running)
    except (ProcessLookupError, PermissionError, ValueError, OSError):
        return True  # Process dead or PID invalid -> stale


def write_override(site_name: str, mk_path: Path, state: SSHState) -> bool:
    """Write the ``.mk`` override file.

    Writes directly via file I/O (the overlay ACLs grant write access).
    Falls back to site-user execution if direct write fails.

    The file must be readable by the site user's Apache process, so
    permissions are set to 0o644.

    Args:
        site_name: OMD site name, e.g. ``'v260'``.
        mk_path: Absolute path to the override ``.mk`` file.

    Returns:
        True on success (file written), False on failure.
    """
    try:
        mk_path.parent.mkdir(parents=True, exist_ok=True)
        mk_path.write_text(_MK_CONTENT)
        mk_path.chmod(0o644)
        return True
    except OSError:
        pass

    # Fallback: write as site user
    try:
        result = run_as_site_user(
            site_name,
            f"cat > {mk_path}",
            state,
            timeout=10,
            input_text=_MK_CONTENT,
        )
        return result.returncode == 0
    except Exception:
        return False


def remove_override(site_name: str, mk_path: Path, state: SSHState) -> bool:
    """Remove the ``.mk`` override file.

    Removes directly via file I/O.  Falls back to site-user execution
    if direct removal fails.  Idempotent — safe to call even when the
    file does not exist.

    Args:
        site_name: OMD site name, e.g. ``'v260'``.
        mk_path: Absolute path to the override ``.mk`` file.

    Returns:
        True on success (file removed or didn't exist), False on failure.
    """
    try:
        mk_path.unlink(missing_ok=True)
        return True
    except OSError:
        pass

    # Fallback: remove as site user
    try:
        result = run_as_site_user(
            site_name,
            f"rm -f {mk_path}",
            state,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False
