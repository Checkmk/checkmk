# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Writable per-site clone of the OMD version directory (clone backend).

An OMD site resolves all code through its ``version`` symlink::

    /omd/sites/<site>/version -> ../../versions/<ver>      (root-owned tree)

This backend copies the pristine version tree into a deploy-user-owned
clone and repoints the symlink (which the site user owns and may swap)::

    /omd/sites/<site>/version -> /omd/dev-versions/<site>/<ver>

The clone keeps the **same basename** as the original version: ``omd``
derives a site's version from the symlink's basename only and
reconstructs ``/omd/versions/<basename>/...`` paths for its own
machinery (hooks, skel, re-exec).  Site runtime follows the symlink into
the clone; omd management tooling keeps operating against the pristine
install.

Compared to the OverlayFS backend there is no mount: activation and
revert are one symlink swap plus a site restart, both executed as the
site user via the sudoers rule (:mod:`sudoers`).  A symlink survives
reboots, so the site always starts with the deployed code, and ``etc/``
/ ``var/`` are never entangled with deploys.

File capabilities (``security.capability`` xattrs, e.g. ``cap_net_raw``
on the ICMP helpers) cannot be copied without root.  Capability-carrying
binaries in the clone are therefore replaced with symlinks back to the
pristine originals, which retain theirs.  If such a binary is itself
deployed later, the deployer replaces the symlink and applies ``setcap``
as today.
"""

from __future__ import annotations

import os
import shlex
import shutil
import stat
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from cmk.dev_deploy.core import output
from cmk.dev_deploy.core.timeouts import CLONE_COPY, GETCAP_SCAN, OVERLAY_CMD
from cmk.dev_deploy.errors import CloneError
from cmk.dev_deploy.site import sudoers

PRISTINE_VERSIONS_DIR = Path("/omd/versions")


def _clone_base(site_name: str) -> Path:
    return sudoers.DEV_VERSIONS_DIR / site_name


def _read_version_link(site_root: Path) -> Path | None:
    """Return the raw (unresolved) target of the site's ``version`` symlink."""
    try:
        return Path(os.readlink(site_root / "version"))
    except OSError:
        return None


def is_clone_active(site_root: Path) -> bool:
    """Whether the ``version`` symlink points at an existing clone."""
    target = _read_version_link(site_root)
    return (
        target is not None
        and target.is_absolute()
        and target.is_relative_to(sudoers.DEV_VERSIONS_DIR)
        and target.is_dir()
    )


def ensure_clone(site_root: Path) -> None:
    """Ensure the site runs on a writable clone of its version directory.

    Idempotent: an active clone is a no-op.  A dangling clone symlink is
    rebuilt in place.  A stale clone (the site's version changed under
    us, e.g. ``omd update`` or a site reinstall) is never deployed into
    or silently discarded -- it raises with recovery instructions.

    Raises:
        CloneError: Unexpected symlink target, stale clone, or build failure.
    """
    site_name = site_root.name
    target = _read_version_link(site_root)
    if target is None:
        raise CloneError(f"Site {site_root} has no readable 'version' symlink")

    if target.is_absolute() and target.is_relative_to(sudoers.DEV_VERSIONS_DIR):
        if target.is_dir():
            output.info(f"Clone active on {site_root} (version -> {target})")
            return
        output.warn(f"Clone {target} is missing (dangling version symlink), rebuilding...")
        _build_clone(PRISTINE_VERSIONS_DIR / target.name, target)
        _activate(site_root, target)
        return

    # normpath, not resolve(): /omd is usually a symlink to /opt/omd and the
    # comparison against /omd/versions must stay lexical.
    pristine = target if target.is_absolute() else Path(os.path.normpath(site_root / target))
    if not pristine.is_relative_to(PRISTINE_VERSIONS_DIR):
        raise CloneError(
            f"Unexpected 'version' symlink target on {site_root}: {target}",
            recovery=(
                "The clone backend only handles sites running on /omd/versions/...\n"
                f"  Inspect: ls -l {site_root}/version"
            ),
        )

    version = pristine.name
    clone = _clone_base(site_name) / version
    if clone.parent.is_dir():
        # Leftovers from interrupted builds are ours and safe to drop.
        for partial in clone.parent.glob(".partial-*"):
            _rmtree(partial, ignore_errors=True)
        stale = sorted(
            d.name
            for d in clone.parent.iterdir()
            if d.is_dir() and d.name != version and not d.name.startswith(".")
        )
        if stale:
            raise CloneError(
                f"Site {site_name} runs version {version}, but stale clone(s) exist "
                f"for: {', '.join(stale)}.\n"
                "The site version changed (omd update or site reinstall) while a "
                "clone existed; refusing to deploy into or silently discard it.",
                recovery=(
                    "Remove the stale clone, then deploy again:\n"
                    f"  cmk-dev-deploy --purge --backend clone --site {site_name}"
                ),
            )

    if clone.is_dir():
        output.info(f"Reusing existing clone {clone}")
    else:
        _build_clone(pristine, clone)
    _activate(site_root, clone)


def teardown_clone(site_root: Path) -> None:
    """Revert the site to the pristine version and delete the clone.

    Leaves the site stopped (parity with the overlay teardown); callers
    decide whether to rebuild (``--full``) or not (``--purge``).  Safe to
    call when no clone is active or the site was deleted -- it then only
    removes leftover clone data.

    Raises:
        CloneError: If the symlink cannot be repointed.
    """
    site_name = site_root.name
    target = _read_version_link(site_root)
    if (
        target is not None
        and target.is_absolute()
        and target.is_relative_to(sudoers.DEV_VERSIONS_DIR)
    ):
        version = target.name
        if not (PRISTINE_VERSIONS_DIR / version).is_dir():
            output.warn(
                f"Pristine version {version} no longer exists; "
                "the site will not start until it is reinstalled"
            )
        output.info(f"Stopping site {site_name} to revert to the pristine version...")
        _run_omd(site_name, "stop")
        _repoint(site_root, f"../../versions/{version}")
        output.info(f"Site {site_name} reverted to version {version} (stopped)")

    base = _clone_base(site_name)
    if base.is_dir():
        _rmtree(base)
        output.info(f"Clone data removed: {base}")


# ---------------------------------------------------------------------------
# Building and activating
# ---------------------------------------------------------------------------


def _build_clone(pristine: Path, clone: Path) -> None:
    """Copy the pristine version tree to *clone* (same basename).

    Copies into a temporary sibling first and renames on success, so an
    interrupted copy can never be mistaken for a complete clone.  Mode
    and timestamps are preserved; ownership deliberately is not (the
    deploy user must own every file), and capabilities are handled by
    :func:`_link_capability_binaries`.
    """
    if not pristine.is_dir():
        raise CloneError(f"Pristine version directory {pristine} does not exist")
    clone.parent.mkdir(parents=True, exist_ok=True)
    partial = clone.parent / f".partial-{clone.name}"
    if partial.exists():
        _rmtree(partial)

    output.info(f"Cloning {pristine} -> {clone} (reflink where supported)...")
    start = time.monotonic()
    try:
        result = subprocess.run(
            [
                "cp",
                "-R",
                "--no-dereference",
                "--preserve=mode,timestamps,links",
                "--reflink=auto",
                str(pristine),
                str(partial),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=CLONE_COPY,
        )
    except subprocess.TimeoutExpired:
        _rmtree(partial, ignore_errors=True)
        raise CloneError(f"Cloning {pristine} timed out after {CLONE_COPY}s") from None
    if result.returncode != 0:
        _rmtree(partial, ignore_errors=True)
        raise CloneError(f"Failed to clone {pristine}: {result.stderr.strip()}")

    _ensure_writable_dirs(partial)
    _link_capability_binaries(pristine, partial)
    partial.rename(clone)
    output.info(f"Clone created in {time.monotonic() - start:.1f}s: {clone}")


def _capability_files(pristine: Path) -> list[Path]:
    """Find files in the pristine tree carrying file capabilities."""
    try:
        result = subprocess.run(
            ["getcap", "-r", str(pristine)],
            capture_output=True,
            text=True,
            check=False,
            timeout=GETCAP_SCAN,
        )
    except (OSError, subprocess.TimeoutExpired):
        output.warn(
            "getcap not available -- capability binaries (e.g. ICMP helpers) "
            "lose their capabilities in the clone"
        )
        return []
    # Line format: "<path> <caps>" (libcap >= 2.41) or "<path> = <caps>".
    return [Path(line.split()[0]) for line in result.stdout.splitlines() if line.strip()]


def _link_capability_binaries(pristine: Path, clone: Path) -> None:
    """Replace capability-carrying binaries in the clone with symlinks.

    Setting ``security.capability`` xattrs requires root; the pristine
    binaries keep theirs, so the clone points back at them.
    """
    for path in _capability_files(pristine):
        try:
            rel = path.relative_to(pristine)
        except ValueError:
            continue
        clone_path = clone / rel
        if clone_path.is_symlink() or not clone_path.is_file():
            continue
        clone_path.unlink()
        clone_path.symlink_to(path)
        output.verbose(f"  Linked capability binary to pristine: {rel}")


def _ensure_writable_dirs(root: Path) -> None:
    """Add owner-write permission to every directory in the clone.

    The pristine tree ships some directories without owner-write (e.g.
    mode 0555 on ``share/check_mk/web/htdocs/openapi``) and the copy
    preserves modes.  In the clone that would block both deploying into
    and deleting those directories, even for the owner.  Files keep
    their modes -- deployers replace files via unlink+rename, which only
    needs a writable parent directory.
    """
    for dirpath, _dirnames, _filenames in os.walk(root):
        mode = os.stat(dirpath).st_mode
        if not mode & stat.S_IWUSR:
            os.chmod(dirpath, mode | stat.S_IWUSR)


def _rmtree(path: Path, *, ignore_errors: bool = False) -> None:
    """``shutil.rmtree`` that copes with read-only directories.

    Clones built before :func:`_ensure_writable_dirs` existed (or made
    read-only afterwards) contain directories the owner cannot delete
    from; the error handler adds owner-write and retries.
    """

    def _retry_writable(func: Callable[[str], object], failed: str, _exc: BaseException) -> None:
        for p in (os.path.dirname(failed), failed):
            try:
                os.chmod(p, os.stat(p).st_mode | stat.S_IWUSR)
            except OSError:
                pass
        func(failed)

    try:
        shutil.rmtree(path, onexc=_retry_writable)
    except OSError:
        if not ignore_errors:
            raise


def _activate(site_root: Path, clone: Path) -> None:
    """Swap the ``version`` symlink to *clone* across a site restart."""
    site_name = site_root.name
    output.info(f"Stopping site {site_name} to activate the clone...")
    _run_omd(site_name, "stop")
    _repoint(site_root, str(clone))
    output.info(f"Starting site {site_name}...")
    _run_omd(site_name, "start")
    output.info(f"Clone activated on {site_root} (version -> {clone})")


def _repoint(site_root: Path, target: str) -> None:
    """Repoint ``<site>/version`` as the site user, who owns the symlink."""
    link = site_root / "version"
    result = sudoers.run_as_site_user(
        site_root.name, f"ln -sfn {shlex.quote(target)} {shlex.quote(str(link))}"
    )
    if result.returncode != 0:
        raise CloneError(f"Failed to repoint {link} -> {target}: {result.stderr.strip()}")


def _run_omd(site_name: str, command: str) -> None:
    result = sudoers.run_as_site_user(site_name, f"omd {command}", timeout=OVERLAY_CMD)
    if result.returncode != 0:
        output.warn(f"omd {command} for site {site_name} exited with {result.returncode}")
