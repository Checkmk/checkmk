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
pristine originals, which retain theirs.  The same helpers are installed
``root:omd`` 0750 by the package postinstall, so a deploy user outside
the ``omd`` group cannot even read them: ``cp`` failures limited to such
files are tolerated and resolved with the same symlinks.  If such a
binary is itself deployed later, the deployer replaces the symlink and
applies ``setcap`` as today.
"""

import contextlib
import os
import re
import shlex
import shutil
import stat
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from cmk.dev_deploy.core import output
from cmk.dev_deploy.core.timeouts import CLONE_COPY, GETCAP_SCAN, OMD_CMD
from cmk.dev_deploy.errors import CloneError
from cmk.dev_deploy.site import sudoers
from cmk.dev_deploy.state.deploy_state import delete_state

PRISTINE_VERSIONS_DIR = Path("/omd/versions")

# GNU cp under LC_ALL=C, failing to read a source file (EACCES).
_CP_UNREADABLE_LINE = re.compile(r"^cp: cannot open '(?P<path>.+)' for reading: Permission denied$")


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
    rebuilt in place.  Stale clones (the site's version changed under
    us, e.g. ``omd update`` or a site reinstall) hold nothing
    irreplaceable and are discarded (see :func:`_discard_stale_clones`).

    Whenever previously deployed files are discarded -- a stale clone is
    removed or a clone is built from scratch -- the incremental deploy
    state is reset alongside (see :func:`_reset_deploy_state`).

    Raises:
        CloneError: Unexpected symlink target, stale clone removal
            failure, or build failure.
    """
    site_name = site_root.name
    _ensure_traversable(sudoers.DEV_VERSIONS_DIR, _clone_base(site_name))
    target = _read_version_link(site_root)
    if target is None:
        raise CloneError(f"Site {site_root} has no readable 'version' symlink")

    if target.is_absolute() and target.is_relative_to(sudoers.DEV_VERSIONS_DIR):
        if target.is_dir():
            output.info(f"Clone active on {site_root} (version -> {target})")
            return
        output.warn(f"Clone {target} is missing (dangling version symlink), rebuilding...")
        _build_clone(PRISTINE_VERSIONS_DIR / target.name, target)
        _reset_deploy_state(site_root)
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
    stale_discarded = _discard_stale_clones(clone.parent, version)
    fresh = not clone.is_dir()
    if fresh:
        _build_clone(pristine, clone)
    else:
        output.info(f"Reusing existing clone {clone}")
    if stale_discarded or fresh:
        _reset_deploy_state(site_root)
    _activate(site_root, clone)


def _discard_stale_clones(base: Path, version: str) -> bool:
    """Drop build leftovers and clones of versions the site no longer runs.

    ``.partial-*`` leftovers from interrupted builds are ours and vanish
    silently.  A clone of a *different* version means the site's version
    changed while a clone existed (``omd update`` or a site reinstall).
    Such a clone holds only a copy of an old pristine tree plus deployed
    files the next deploy rebuilds from the repo -- site configuration
    and runtime data (``etc/``, ``var/``) never live in the clone -- so
    it is discarded, loudly.

    Raises:
        CloneError: A stale clone could not be removed.
    """
    if not base.is_dir():
        return False
    for partial in base.glob(".partial-*"):
        _rmtree(partial, ignore_errors=True)
    stale = sorted(
        d.name
        for d in base.iterdir()
        if d.is_dir() and d.name != version and not d.name.startswith(".")
    )
    if not stale:
        return False
    output.warn(
        f"Site version changed to {version} while clone(s) existed "
        f"(omd update or site reinstall); discarding stale clone(s): {', '.join(stale)}"
    )
    for name in stale:
        stale_clone = base / name
        try:
            _rmtree(stale_clone)
        except OSError as e:
            raise CloneError(
                f"Failed to remove stale clone {stale_clone}: {e}",
                recovery=f"Remove it manually, then deploy again:\n  rm -rf {stale_clone}",
            ) from e
    return True


def _reset_deploy_state(site_root: Path) -> None:
    """Reset the incremental deploy state after deployed files were discarded.

    A freshly built clone contains exactly the pristine files.  Deploy
    state recorded against a previous tree would let change detection
    skip deployers whose output no longer exists, silently leaving the
    site on pristine code.
    """
    delete_state(site_root)
    output.verbose("  Incremental deploy state reset (deploying everything)")


def teardown_clone(site_root: Path) -> None:
    """Revert the site to the pristine version and delete the clone.

    Leaves the site stopped; callers decide whether to rebuild
    (``--full``) or not (``--purge``).  Safe to call when no clone is
    active or the site was deleted -- it then only removes leftover
    clone data.

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
        stop_elapsed = _run_omd(site_name, "stop")
        _repoint(site_root, f"../../versions/{version}")
        output.info(
            f"Site {site_name} reverted to version {version} (stopped in {stop_elapsed:.1f}s)"
        )

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
    deploy user must own every file), capabilities are handled by
    :func:`_link_capability_binaries`, and files the deploy user cannot
    read by :func:`_link_unreadable_binaries`.
    """
    if not pristine.is_dir():
        raise CloneError(f"Pristine version directory {pristine} does not exist")
    clone.parent.mkdir(parents=True, exist_ok=True)
    _ensure_traversable(clone.parent)
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
            env={**os.environ, "LC_ALL": "C"},  # _CP_UNREADABLE_LINE parses the messages
        )
    except subprocess.TimeoutExpired:
        _rmtree(partial, ignore_errors=True)
        raise CloneError(f"Cloning {pristine} timed out after {CLONE_COPY}s") from None
    if result.returncode != 0:
        unreadable = _unreadable_pristine_files(pristine, result.stderr)
        if unreadable is None:
            _rmtree(partial, ignore_errors=True)
            raise CloneError(f"Failed to clone {pristine}: {result.stderr.strip()}")
        _link_unreadable_binaries(pristine, partial, unreadable)

    _ensure_writable_dirs(partial)
    _link_capability_binaries(pristine, partial)
    partial.rename(clone)
    output.info(f"Clone created in {time.monotonic() - start:.1f}s: {clone}")


def _unreadable_pristine_files(pristine: Path, cp_stderr: str) -> list[Path] | None:
    """Map ``cp`` stderr onto unreadable pristine files, ``None`` on anything else.

    A copy failure is only tolerable when every reported error is an
    unreadable regular file inside the pristine tree (the ``root:omd``
    0750 capability/setuid helpers).  Unreadable directories or any
    other ``cp`` error keep the copy fatal: ``None``.
    """
    files = []
    for line in filter(None, map(str.strip, cp_stderr.splitlines())):
        match = _CP_UNREADABLE_LINE.match(line)
        if match is None:
            return None
        path = Path(match["path"])
        if not path.is_relative_to(pristine):
            return None
        try:
            if not stat.S_ISREG(path.lstat().st_mode):
                return None
        except OSError:
            return None
        files.append(path)
    return files or None


def _link_unreadable_binaries(pristine: Path, clone: Path, files: list[Path]) -> None:
    """Symlink files the deploy user cannot read back to the pristine tree.

    The package postinstall restricts a few helper binaries (check_icmp,
    icmpsender, mkeventd_open514, ...) to ``root:omd`` 0750, so ``cp``
    skips them for a deploy user outside the ``omd`` group.  A copy
    would lose their capabilities or setuid bit anyway, so they point
    back at the pristine originals -- exactly like the readable
    capability binaries in :func:`_link_capability_binaries`.
    """
    for path in files:
        rel = path.relative_to(pristine)
        clone_path = clone / rel
        clone_path.unlink(missing_ok=True)
        clone_path.symlink_to(path)
        output.verbose(f"  Linked unreadable binary to pristine: {rel}")
    output.info(
        f"{len(files)} binaries are not readable (root:omd) and were "
        "linked to the pristine originals instead"
    )


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
    except OSError, subprocess.TimeoutExpired:
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


def _ensure_traversable(*dirs: Path) -> None:
    """Give existing *dirs* group/other read+execute permission.

    The site user resolves its ``version`` symlink through these
    deploy-user-owned directories.  Each is created only once, ever, so
    one created under a restrictive umask (e.g. 027) locks the site user
    out of the clone permanently: every service fails on start with
    EACCES.  ``main()`` forces umask 022 for anything created from now
    on; this heals directories created by earlier versions of this tool.
    """
    for path in dirs:
        try:
            mode = path.stat().st_mode
            if mode & 0o055 != 0o055:
                path.chmod(mode | 0o055)
        except FileNotFoundError:
            continue
        except OSError as exc:
            output.warn(
                f"{path} is not readable by the site user and cannot be fixed "
                f"({exc}); fix manually: chmod go+rx {path}"
            )


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
            with contextlib.suppress(OSError):
                os.chmod(p, os.stat(p).st_mode | stat.S_IWUSR)
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
    stop_elapsed = _run_omd(site_name, "stop")
    _repoint(site_root, str(clone))
    output.info(f"Starting site {site_name}...")
    start_elapsed = _run_omd(site_name, "start")
    output.info(
        f"Clone activated on {site_root} "
        f"(omd stop {stop_elapsed:.1f}s, omd start {start_elapsed:.1f}s)"
    )


def _repoint(site_root: Path, target: str) -> None:
    """Repoint ``<site>/version`` as the site user, who owns the symlink."""
    link = site_root / "version"
    result = sudoers.run_as_site_user(
        site_root.name, f"ln -sfn {shlex.quote(target)} {shlex.quote(str(link))}"
    )
    if result.returncode != 0:
        raise CloneError(f"Failed to repoint {link} -> {target}: {result.stderr.strip()}")


def _run_omd(site_name: str, command: str) -> float:
    """Run an omd command as the site user, returning the elapsed seconds."""
    start = time.monotonic()
    result = sudoers.run_as_site_user(site_name, f"omd {command}", timeout=OMD_CMD)
    elapsed = time.monotonic() - start
    if result.returncode != 0:
        output.warn(f"omd {command} for site {site_name} exited with {result.returncode}")
    return elapsed
