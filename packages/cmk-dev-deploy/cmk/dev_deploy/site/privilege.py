# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Privilege helpers for cmk-dev-deploy.

Centralizes user-switching and privilege escalation so the rest of the
codebase never hard-codes ``sudo``.  The primary goal is to let the tool
run **without** an outer ``sudo`` wrapper.

Strategy (after overlay setup):

* Commands that must run as the **site user** (``omd restart``, etc.)
  are executed via SSH to ``<site>@localhost``.  During overlay setup an
  SSH public key is injected into the site user's ``authorized_keys``
  on the overlay upper layer (reverted on ``--purge``).

* If SSH is not available, falls back to ``sudo --login -u <site>``.

* Commands that need **root** (``mount``, ``umount``, ``setfacl``, etc.)
  use ``sudo`` directly — the tool prompts for a password if needed.
"""

from __future__ import annotations

import dataclasses
import getpass
import os
import subprocess
from pathlib import Path

from cmk.dev_deploy.core import output


@dataclasses.dataclass
class SSHState:
    """Mutable SSH-related state threaded through the deploy session."""

    deploy_key_path: Path | None = None
    ssh_available: dict[str, bool] = dataclasses.field(default_factory=dict)

    def clear_ssh_cache(self) -> None:
        """Clear the SSH connectivity cache."""
        self.ssh_available.clear()


# ---------------------------------------------------------------------------
# Real user detection
# ---------------------------------------------------------------------------


def get_real_user() -> str:
    """Return the actual human user, even when running under ``sudo``.

    Checks ``SUDO_USER`` first (set by sudo), then falls back to
    ``getpass.getuser()``.
    """
    return os.environ.get("SUDO_USER") or getpass.getuser()


# ---------------------------------------------------------------------------
# SSH key injection for site-user commands
# ---------------------------------------------------------------------------

_SSH_MARKER = "# cmk-dev-deploy auto-injected key"


_DEPLOY_KEY_NAME = "cmk-dev-deploy"
"""Dedicated deploy key name (no passphrase, not on Yubikey).

Looked up as ``~/.ssh/cmk-dev-deploy`` before falling back to the
user's default SSH keys.  Generate with::

    ssh-keygen -t ed25519 -f ~/.ssh/cmk-dev-deploy -N ""
"""


def _get_deploy_pubkey(state: SSHState) -> str | None:
    """Return the deploy user's SSH public key, or None if not found.

    Prefers a dedicated ``~/.ssh/cmk-dev-deploy`` key (passphrase-free,
    works without Yubikey touch after reboot).  Falls back to the
    user's default keys.

    Sets ``state.deploy_key_path`` to the corresponding private key
    so that :func:`_ssh_cmd` can pass ``-i`` to the SSH client.
    """
    home = Path.home()
    # When running under sudo, use the real user's home
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        home = Path(f"/home/{sudo_user}")

    # Dedicated deploy key first (no passphrase, no Yubikey)
    deploy_pub = home / ".ssh" / f"{_DEPLOY_KEY_NAME}.pub"
    deploy_priv = home / ".ssh" / _DEPLOY_KEY_NAME
    if deploy_pub.is_file() and deploy_priv.is_file():
        state.deploy_key_path = deploy_priv
        return deploy_pub.read_text().strip()

    for name in ("id_ed25519.pub", "id_rsa.pub", "id_ecdsa.pub"):
        # Check both ~/.ssh/ and ~/.ssh/<subdir>/ (some setups nest keys)
        for candidate in (
            home / ".ssh" / name,
            *sorted((home / ".ssh").glob(f"*/{name}")),
        ):
            if candidate.is_file():
                # Derive private key path by removing .pub suffix
                privkey = candidate.with_suffix("")
                if privkey.is_file():
                    state.deploy_key_path = privkey
                return candidate.read_text().strip()
    return None


def inject_ssh_key(site_root: Path, state: SSHState) -> bool:
    """Inject the deploy user's SSH public key into the site user's authorized_keys.

    Operates on the overlay so the key is removed on ``--purge``.
    Safe to call multiple times (idempotent via marker comment).

    sshd requires ``~/.ssh`` (mode 700) and ``authorized_keys`` (mode 600)
    to be owned by the target user, so we use root to create them with the
    correct ownership.

    Returns True if a key was injected (or already present), False on failure.
    """
    pubkey = _get_deploy_pubkey(state)
    if pubkey is None:
        return False

    site_name = site_root.name
    ssh_dir = site_root / ".ssh"
    auth_keys = ssh_dir / "authorized_keys"

    try:
        # Check if already injected
        if auth_keys.exists():
            try:
                existing = auth_keys.read_text()
            except OSError:
                # File exists but not readable by deploy user — read as root
                result = run_as_root(["cat", str(auth_keys)])
                existing = result.stdout if result.returncode == 0 else ""
            if _SSH_MARKER in existing:
                return True

        # Create .ssh dir owned by site user (sshd requires this)
        run_as_root(["mkdir", "-p", "-m", "700", str(ssh_dir)])
        run_as_root(["chown", site_name, str(ssh_dir)])

        # Append key with marker, set ownership and perms
        entry = f"{pubkey} {_SSH_MARKER}\n"
        # Write via shell to handle append correctly
        result = run_as_root(
            ["bash", "-c", f"cat >> {auth_keys}"],
            input=entry,
        )
        if result.returncode != 0:
            return False
        run_as_root(["chmod", "600", str(auth_keys)])
        run_as_root(["chown", site_name, str(auth_keys)])
        output.verbose(f"SSH key injected for site user {site_name}")
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Run command as site user (SSH → sudo fallback)
# ---------------------------------------------------------------------------


def _check_ssh(site_name: str, state: SSHState) -> bool:
    """Test whether SSH to ``<site>@localhost`` works."""
    if state.deploy_key_path is None:
        # Ensure key path is discovered even if inject_ssh_key hasn't run
        _get_deploy_pubkey(state)
    if site_name in state.ssh_available:
        return state.ssh_available[site_name]
    try:
        result = subprocess.run(
            [*_ssh_cmd(site_name, state), "true"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        state.ssh_available[site_name] = False
        output.warn(
            f"SSH to {site_name}@localhost timed out, "
            "falling back to sudo. "
            "Re-run with --purge to re-inject the SSH key."
        )
        return False
    ok = result.returncode == 0
    state.ssh_available[site_name] = ok
    if not ok:
        detail = result.stderr.strip() or f"exit {result.returncode}"
        output.warn(
            f"SSH to {site_name}@localhost failed ({detail}), "
            "falling back to sudo. "
            "Re-run with --purge to re-inject the SSH key."
        )
    return ok


def _ssh_cmd(site_name: str, state: SSHState) -> list[str]:
    """Build an SSH command list for the site user."""
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=3",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "LogLevel=ERROR",
    ]
    if state.deploy_key_path is not None:
        cmd.extend(["-i", str(state.deploy_key_path)])
    cmd.extend([f"{site_name}@localhost"])
    return cmd


def _ssh_cmd_with_command(site_name: str, command: str, state: SSHState) -> list[str]:
    """Build an SSH command list for the site user with a command."""
    return [*_ssh_cmd(site_name, state), command]


def _sudo_cmd(site_name: str, command: str) -> list[str]:
    """Build a sudo --login command list for the site user."""
    return [
        "sudo",
        "--login",
        "-u",
        site_name,
        "--",
        "bash",
        "-c",
        command,
    ]


def run_as_site_user(
    site_name: str,
    command: str,
    state: SSHState,
    *,
    timeout: int = 30,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run *command* as the OMD site user.

    Tries SSH first (no sudo needed).  Falls back to ``sudo --login -u``
    if SSH is unavailable.

    Args:
        site_name: OMD site name (= site user name).
        command: Shell command to execute in the site user's login env.
        state: SSH state for key path and connectivity cache.
        timeout: Maximum seconds to wait.
        input_text: Optional stdin to pass to the command.

    Returns:
        Completed process result (``check=False``).

    Raises:
        subprocess.TimeoutExpired: If the command exceeds *timeout*.
    """
    if _check_ssh(site_name, state):
        cmd = _ssh_cmd_with_command(site_name, command, state)
    else:
        cmd = _sudo_cmd(site_name, command)

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
        input=input_text,
    )


# ---------------------------------------------------------------------------
# Run command as root (only when truly needed)
# ---------------------------------------------------------------------------


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
    if os.geteuid() == 0:
        full_cmd = cmd
    else:
        full_cmd = ["sudo", "-n", *cmd]
    result: subprocess.CompletedProcess[str] = subprocess.run(  # type: ignore[call-overload]
        full_cmd,
        capture_output=True,
        text=True,
        check=False,
        **kwargs,
    )
    return result


# ---------------------------------------------------------------------------
# Setcap helper (best-effort)
# ---------------------------------------------------------------------------


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
