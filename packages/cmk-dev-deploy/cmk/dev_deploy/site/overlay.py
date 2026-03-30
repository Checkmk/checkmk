# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""OverlayFS management for cmk-dev-deploy.

Provides transparent filesystem overlay on OMD site directories so that all
deployed files land in an upper layer that can be trivially reverted.  The
overlay is mounted automatically on the first deploy and persists across
subsequent deploys.  After a reboot the mount is gone but the upper directory
survives on disk; the next deploy re-mounts with the existing upper layer,
restoring all previous changes.

OMD sites use top-level symlinks (``bin/``, ``lib/``, ``share/``) pointing to
the shared version directory (``/omd/versions/<ver>/``).  Since OverlayFS only
intercepts writes within its mount point, writes that follow these symlinks
would bypass the overlay.  To fix this, the first mount "materializes" these
symlinks: their targets are copied into the overlay upper layer so they become
real directories.  Subsequent mounts reuse the existing upper layer.

Requires ``sudo`` for ``mount``/``umount`` operations (one-time per session).
The tool requests sudo internally — no outer ``sudo`` wrapper is needed.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from cmk.dev_deploy.core import output
from cmk.dev_deploy.core.timeouts import OVERLAY_CMD
from cmk.dev_deploy.errors import OverlayError
from cmk.dev_deploy.site.privilege import (
    get_real_user,
    inject_ssh_key,
    run_as_root,
    SSHState,
)

# Persistent storage for overlay upper/work directories.
# /var/tmp survives reboots (unlike /tmp which may be tmpfs).
_OVERLAY_BASE = Path("/var/tmp/cmk-dev-deploy")  # nosec B108

# File in the overlay base that records which version was materialized.
# Used to detect version changes that require re-materialization.
_VERSION_MARKER = "materialized_version"


def _run_omd_via_sudo(site_name: str, command: str) -> None:
    """Run an omd command as the site user via sudo.

    Used during overlay setup/teardown when SSH is unavailable.
    """
    subprocess.run(
        ["sudo", "--login", "-u", site_name, "--", "bash", "-c", f"omd {command}"],
        capture_output=True,
        text=True,
        check=False,
        timeout=OVERLAY_CMD,
    )


def _upper_dir(site_root: Path) -> Path:
    return _OVERLAY_BASE / site_root.name / "upper"


def _work_dir(site_root: Path) -> Path:
    return _OVERLAY_BASE / site_root.name / "work"


def _site_overlay_dir(site_root: Path) -> Path:
    return _OVERLAY_BASE / site_root.name


def _ensure_overlay_dirs(site_overlay: Path) -> None:
    """Ensure the site overlay directory exists and is writable by the deploy user.

    Previous runs under ``sudo`` may have created these directories as root.
    This function creates the directory if needed and chowns it (and the parent
    base dir) to the real deploy user so that subsequent operations like
    ``mkdir``, marker file writes, and ``du`` work without root.
    """
    user = get_real_user()
    # Create base + site dir if they don't exist
    run_as_root(["mkdir", "-p", str(site_overlay)])
    # Chown the site overlay dir (and base) to the deploy user
    run_as_root(["chown", user, str(_OVERLAY_BASE), str(site_overlay)])


def _version_dir(site_root: Path) -> Path | None:
    """Determine the OMD version directory from the site's ``version`` symlink.

    Returns ``None`` if the symlink does not exist or cannot be resolved.
    """
    version_link = site_root / "version"
    if not version_link.is_symlink():
        return None
    try:
        target = os.readlink(version_link)
        return (version_link.parent / target).resolve()
    except OSError:
        return None


def _find_sub_mounts(mount_point: str) -> list[str]:
    """Return mount points that are nested under *mount_point*, deepest first.

    Parses ``/proc/mounts`` to find any filesystems mounted within the given
    path (e.g. a tmpfs on ``<site>/tmp``).  Returns them in reverse order so
    that the deepest mounts are unmounted first.
    """
    try:
        mounts = Path("/proc/mounts").read_text()
    except OSError:
        return []
    prefix = mount_point.rstrip("/") + "/"
    sub_mounts = [
        parts[1]
        for line in mounts.splitlines()
        if len(parts := line.split()) >= 2 and parts[1].startswith(prefix)
    ]
    # Deepest first so unmount order is correct
    sub_mounts.sort(key=lambda p: p.count("/"), reverse=True)
    return sub_mounts


def is_overlay_active(site_root: Path) -> bool:
    """Check whether an OverlayFS is currently mounted on *site_root*.

    Parses ``/proc/mounts`` for an overlay entry whose mount point matches
    the resolved site root path.
    """
    resolved = str(site_root.resolve())
    try:
        mounts = Path("/proc/mounts").read_text()
    except OSError:
        return False
    for line in mounts.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "overlay" and parts[1] == resolved:
            return True
    return False


def _chown_upper(upper: Path) -> None:
    """Make the deploy user own everything in the overlay upper layer.

    After materialization, the upper layer contains root-owned files (from
    ``rsync -a``).  OverlayFS preserves file ownership on copy-up, so any
    metadata operation (``chmod``, ``copystat``, xattr) on a root-owned file
    fails with ``EPERM`` for a non-root user — even with ACL write access.

    The definitive fix: ``chown -R`` the entire upper layer to the deploy
    user.  This makes all file operations work naturally without ACLs or
    special copy functions.  Apache/WSGI still works because it reads files
    through the overlay merged view where permissions are checked against
    the lower layer's metadata.
    """
    user = get_real_user()
    start = time.monotonic()
    result = run_as_root(["chown", "-R", user, str(upper)])
    elapsed = time.monotonic() - start
    if result.returncode != 0:
        output.warn(f"Failed to chown upper layer: {result.stderr.strip()}")
    else:
        output.verbose(f"Upper layer ownership set to {user} ({elapsed:.1f}s)")


def _materialize_symlinks(site_root: Path) -> None:
    """Copy version-dir symlink targets into the overlay upper layer.

    OMD sites have top-level symlinks (``bin/``, ``lib/``, ``share/``, etc.)
    pointing to the shared version directory.  OverlayFS only intercepts
    writes within its mount point; following these symlinks escapes the
    overlay.

    This function copies the contents of each symlink target into the
    overlay upper layer so they become real directories.  Must be called
    **before** mounting the overlay (operates on the upper dir directly).

    Only runs on first mount; subsequent mounts reuse the populated upper
    layer.  A version marker detects version changes that require
    re-materialization.
    """
    upper = _upper_dir(site_root)
    version_dir = _version_dir(site_root)
    if version_dir is None:
        output.warn("Could not determine version directory, skipping symlink materialization")
        return

    version_string = version_dir.name
    marker_path = _site_overlay_dir(site_root) / _VERSION_MARKER

    # Check if already materialized for this version
    if marker_path.exists():
        stored_version = marker_path.read_text().strip()
        if stored_version == version_string:
            return
        # Version changed — need to re-materialize
        output.warn(
            f"Version changed ({stored_version} -> {version_string}), "
            "re-materializing overlay upper layer..."
        )
        # Clear existing upper contents and per-directory markers (stale version data)
        run_as_root(["rm", "-rf", str(upper)])
        upper.mkdir(parents=True, exist_ok=True)
        markers = _site_overlay_dir(site_root) / "markers"
        if markers.exists():
            run_as_root(["rm", "-rf", str(markers)])

    total_start = time.monotonic()
    materialized: list[tuple[str, str, float]] = []

    # Per-directory completion markers to detect interrupted materializations.
    # If a directory exists but its marker does not, the previous rsync was
    # interrupted and the directory must be re-synced from scratch.
    markers_dir = _site_overlay_dir(site_root) / "markers"
    markers_dir.mkdir(parents=True, exist_ok=True)

    # Iterate the version directory instead of the site directory.
    # The site directory (drwxr-x--x, owned by site user) is not readable
    # by the deploy user, but the version directory (/omd/versions/<ver>,
    # mode 775 root:root) is world-readable.  Each subdirectory in the
    # version dir corresponds to a symlink in the site dir (bin/, lib/, etc.).
    for target in sorted(version_dir.iterdir()):
        if not target.is_dir():
            continue
        entry_name = target.name

        upper_entry = upper / entry_name
        dir_marker = markers_dir / f"{entry_name}.done"

        if upper_entry.exists() and upper_entry.is_dir():
            if dir_marker.exists():
                continue  # fully materialized on a previous run
            # Directory exists but marker is missing — interrupted rsync.
            # Remove the partial directory and redo.
            output.warn(f"Incomplete materialization of {entry_name}/, re-syncing...")
            run_as_root(["rm", "-rf", str(upper_entry)])

        dir_start = time.monotonic()
        upper_entry.mkdir(parents=True, exist_ok=True)

        # -a preserves ownership (root) for Apache/WSGI.
        # -A preserves POSIX ACLs which grant the deploy user write access
        # to root-owned directories.
        result = run_as_root(
            ["rsync", "-aA", f"{target}/", f"{upper_entry}/"],
        )
        dir_elapsed = time.monotonic() - dir_start

        if result.returncode != 0:
            output.warn(f"Failed to materialize {entry_name}/: {result.stderr.strip()}")
            continue

        # Mark this directory as fully materialized
        dir_marker.write_text("ok")

        # Get size of materialized directory
        size_result = subprocess.run(
            ["du", "-sh", str(upper_entry)],
            capture_output=True,
            text=True,
            check=False,
        )
        size_str = size_result.stdout.split()[0] if size_result.returncode == 0 else "?"

        materialized.append((entry_name, size_str, dir_elapsed))

    total_elapsed = time.monotonic() - total_start

    # Print column-aligned materialization table
    if materialized and output.get_verbosity() >= output.Verbosity.VERBOSE:
        # Compute column widths for alignment
        max_name = max(len(n) + 1 for n, _, _ in materialized)  # +1 for trailing /
        max_size = max(len(s) for _, s, _ in materialized)
        for name, size, elapsed in materialized:
            output.verbose(
                f"  Materialized {name + '/':<{max_name}s}  {size:>{max_size}s}  {elapsed:.1f}s"
            )

    if materialized:
        names = ", ".join(f"{name}/" for name, _, _ in materialized)
        output.info(f"Materialized {len(materialized)} symlink(s) in {total_elapsed:.1f}s: {names}")

        # Set default ACLs so directories created by the deployer (after
        # _clean_package removes and rsync recreates them) inherit write
        # access.  omd-setup-version-for-dev only sets access ACLs, not
        # default ACLs, so rsync -aA copies them but new dirs won't inherit.
        _chown_upper(upper)

        # Write version marker so we skip next time
        marker_path.write_text(version_string)
    # Still write marker if upper dir has content
    elif not marker_path.exists() and upper.exists():
        marker_path.write_text(version_string)


def _restore_capabilities(site_root: Path) -> None:
    """Re-apply file capabilities that OverlayFS may have stripped.

    Reads the deploy manifest for binaries with ``SETCAP_NET_RAW`` in
    their ``post_install`` list and ensures the capability is set on the
    merged overlay view.  This runs after every overlay mount because
    copy-up or the mount itself can strip ``security.capability`` xattrs.
    """
    from cmk.dev_deploy.manifest.reader import get_install_specs
    from cmk.dev_deploy.site.privilege import try_setcap
    from cmk.dev_deploy.types import PostInstallAction

    try:
        specs = get_install_specs()
    except FileNotFoundError:
        output.verbose("Manifest not found, skipping capability restoration")
        return

    cap = "cap_net_raw+ep"
    for spec in specs:
        if PostInstallAction.SETCAP_NET_RAW not in spec.post_install:
            continue
        binary = site_root / spec.install_dest
        if not binary.is_file():
            continue
        output.verbose(f"Restoring {cap} on {binary.name}")
        try_setcap(binary, cap)


def ensure_overlay(site_root: Path, state: SSHState) -> None:
    """Ensure an OverlayFS is mounted on *site_root*.

    If already mounted, this is a no-op.  If the upper directory exists from
    a previous session (e.g. after reboot), re-mounts with the existing data.
    Otherwise creates fresh upper/work directories, materializes version-dir
    symlinks, and mounts.

    Requires ``sudo`` for the ``mount`` call.

    Raises:
        OverlayError: If the mount command fails.
    """
    if is_overlay_active(site_root):
        output.info(f"Overlay active on {site_root}")
        return

    upper = _upper_dir(site_root)
    work = _work_dir(site_root)
    site_overlay = _site_overlay_dir(site_root)

    # Ensure the overlay base directory is owned by the deploy user so
    # subsequent file operations (mkdir, marker writes) work without root.
    _ensure_overlay_dirs(site_overlay)

    resuming = upper.exists() and any(upper.iterdir())

    # Create directories
    upper.mkdir(parents=True, exist_ok=True)
    # work dir must be empty for overlayfs
    if work.exists():
        run_as_root(["rm", "-rf", str(work)])
    work.mkdir(parents=True, exist_ok=True)

    # Materialize version-dir symlinks into upper layer (before mounting).
    # On resume, checks version marker and skips if already done.
    _materialize_symlinks(site_root)

    site_name = site_root.name
    resolved = str(site_root.resolve())
    opts = f"lowerdir={resolved},upperdir={upper},workdir={work}"

    # Stop site so processes start on the overlay after mount
    output.info(f"Stopping site {site_name} for overlay mount...")
    # During overlay setup we must use sudo (SSH not yet available)
    _run_omd_via_sudo(site_name, "stop")

    result = run_as_root(
        ["mount", "-t", "overlay", "overlay", "-o", opts, resolved],
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        # Try to restart the site even if mount failed
        _run_omd_via_sudo(site_name, "start")
        raise OverlayError(
            f"Failed to mount overlay on {site_root}: {stderr}",
            recovery=(
                "Ensure you have sudo privileges and the kernel supports OverlayFS.\n"
                "Check: modprobe overlay && cat /proc/filesystems | grep overlay"
            ),
        )

    # Inject SSH key so subsequent deploys can run omd commands without sudo.
    # Must happen after mount but before site start, while we still have
    # sudo access from the overlay setup phase.
    inject_ssh_key(site_root, state)

    # Fix home directory ownership for sshd StrictModes.
    # _chown_upper set the entire upper layer to the deploy user, but sshd
    # requires the home directory to be owned by the site user and not be
    # group/world-writable.  Fix the upper layer's root dir (which maps to
    # the site home on the merged view).
    run_as_root(["chown", site_name, str(upper)])
    run_as_root(["chmod", "755", str(upper)])

    # Clear cached SSH check results -- the old overlay (and its key) is
    # gone, so any cached True/False from teardown is stale.
    state.clear_ssh_cache()

    # Restore file capabilities stripped by the overlay mount.
    # OverlayFS may drop security.capability xattrs on copy-up, so
    # binaries like icmpsender/icmpreceiver lose cap_net_raw.  Re-apply
    # capabilities listed in the manifest before starting the site.
    _restore_capabilities(site_root)

    # Start site on the overlay.
    # Use sudo directly — sshd isn't running yet (it starts with omd).
    output.info(f"Starting site {site_name}...")
    _run_omd_via_sudo(site_name, "start")

    if resuming:
        output.info(f"Overlay resumed on {site_root} (existing changes preserved)")
    else:
        output.info(f"Overlay mounted on {site_root}")


def teardown_overlay(site_root: Path) -> None:
    """Unmount the overlay and remove upper/work directories.

    Stops the site before unmounting (services hold open file handles on the
    overlay) and does NOT restart it afterwards — callers decide whether to
    restart (``--full`` re-mounts and deploys; ``--purge`` leaves the site
    stopped so the user can start it manually).

    If no overlay is mounted, only cleans up directories (if they exist).

    Requires ``sudo`` for the ``umount`` and ``omd stop`` calls.

    Raises:
        OverlayError: If the unmount command fails.
    """
    if is_overlay_active(site_root):
        site_name = site_root.name
        resolved = str(site_root.resolve())

        # Stop site so processes release file handles on the overlay.
        # Use sudo directly — the SSH key lives on the overlay we're
        # about to destroy, so SSH is unreliable here.
        output.info(f"Stopping site {site_name} for overlay teardown...")
        _run_omd_via_sudo(site_name, "stop")

        # Unmount any sub-mounts (e.g. tmpfs on tmp/) before the overlay
        for sub_mount in _find_sub_mounts(resolved):
            run_as_root(["umount", sub_mount])

        # Try normal unmount first
        result = run_as_root(["umount", resolved])
        if result.returncode != 0:
            # Kill any remaining processes holding the mount busy
            output.warn("Mount still busy, killing remaining processes...")
            run_as_root(["fuser", "-km", resolved])
            # Retry unmount
            result = run_as_root(["umount", resolved])
        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise OverlayError(
                f"Failed to unmount overlay on {site_root}: {stderr}",
                recovery=(
                    "Ensure no processes have open files under the site directory.\n"
                    f"Try: sudo lsof +D {site_root}"
                ),
            )
        output.info(f"Overlay unmounted from {site_root}")

    # Clean up upper/work directories and version marker
    site_overlay_dir = _site_overlay_dir(site_root)
    if site_overlay_dir.exists():
        run_as_root(["rm", "-rf", str(site_overlay_dir)])
        output.info(f"Overlay data removed: {site_overlay_dir}")


def overlay_upper_size(site_root: Path) -> str | None:
    """Return the disk usage of the overlay upper directory, or None."""
    upper = _upper_dir(site_root)
    if not upper.exists():
        return None
    result = subprocess.run(
        ["du", "-sh", str(upper)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.split()[0]
    return None
