# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Per-site sudoers rule management for the clone backend.

The clone backend runs site commands (``omd stop/start``, symlink swaps)
through a single privilege mechanism: a per-(user, site) sudoers drop-in

    <user> ALL=(<site>) NOPASSWD: ALL

Every run probes for the rule non-interactively (:func:`probe`).  If it is
missing, :func:`bootstrap` shows the exact drop-in content and asks for
one-time permission to install it (``visudo -cf`` validated — a malformed
file in ``/etc/sudoers.d/`` makes sudo fail closed system-wide).  After
bootstrap, no deploy, restart, ``--full``, or ``--purge`` ever prompts
for a password again.

There is deliberately no SSH path and no fallback chain here — the overlay
backend keeps using :mod:`cmk.dev_deploy.site.privilege` unchanged.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from cmk.dev_deploy.core import output
from cmk.dev_deploy.errors import SudoersError
from cmk.dev_deploy.site.privilege import get_real_user

SUDOERS_DIR = Path("/etc/sudoers.d")

DEV_VERSIONS_DIR = Path("/omd/dev-versions")
"""Deploy-user-owned base directory holding the writable version clones."""

_PROBE_TIMEOUT = 10
_SETUP_TIMEOUT = 60


def drop_in_path(site_name: str) -> Path:
    """Return the path of the per-(user, site) sudoers drop-in.

    sudo skips files in ``sudoers.d`` whose names contain dots, so dots
    (e.g. in user names) are replaced with underscores.
    """
    name = f"cmk-dev-deploy-{get_real_user()}-{site_name}".replace(".", "_")
    return SUDOERS_DIR / name


def rule_content(site_name: str) -> str:
    """Return the sudoers rule granting a passwordless shell as the site user."""
    return f"{get_real_user()} ALL=({site_name}) NOPASSWD: ALL\n"


def probe(site_name: str) -> bool:
    """Check non-interactively whether commands can run as the site user.

    ``sudo -n`` can never prompt; a missing rule fails within milliseconds.
    """
    try:
        result = subprocess.run(
            ["sudo", "-n", "-u", site_name, "--", "true"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_PROBE_TIMEOUT,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0


def run_as_site_user(
    site_name: str,
    command: str,
    *,
    timeout: int = 30,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a shell command in the site user's login environment.

    Uses the sudoers rule (``sudo -n`` — never prompts).  Callers are
    expected to have verified the rule via :func:`probe` / :func:`bootstrap`.

    Raises:
        subprocess.TimeoutExpired: If the command exceeds *timeout*.
    """
    return subprocess.run(
        ["sudo", "-n", "--login", "-u", site_name, "--", "bash", "-c", command],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
        input=input_text,
    )


# ---------------------------------------------------------------------------
# Bootstrap (consent flow) and setup helpers
# ---------------------------------------------------------------------------


def admin_setup_commands(site_name: str) -> str:
    """Return the manual setup commands for an administrator."""
    rule = rule_content(site_name).strip()
    user = get_real_user()
    return (
        f"rule=$(mktemp)\n"
        f"echo '{rule}' > \"$rule\"\n"
        f'sudo visudo -cf "$rule"\n'
        f'sudo install -m 0440 -o root -g root "$rule" {drop_in_path(site_name)}\n'
        f'rm "$rule"\n'
        f"sudo mkdir -p {DEV_VERSIONS_DIR}\n"
        f"sudo chown {user} {DEV_VERSIONS_DIR}"
    )


def _admin_recovery(site_name: str) -> str:
    indented = "\n".join(f"    {line}" for line in admin_setup_commands(site_name).splitlines())
    return f"Ask an administrator to run:\n{indented}"


def bootstrap(site_name: str) -> None:
    """Install the per-site sudoers rule after explicit user consent.

    Non-interactive runs and declined prompts raise :class:`SudoersError`
    carrying the manual setup instructions.

    Raises:
        SudoersError: No TTY, consent declined, validation or install failed.
    """
    rule = rule_content(site_name)
    path = drop_in_path(site_name)

    if not sys.stdin.isatty():
        raise SudoersError(
            f"No sudoers rule allows running commands as site user '{site_name}', "
            "and there is no interactive terminal to set one up.",
            recovery=_admin_recovery(site_name),
        )

    output.info("The clone backend runs site commands via a per-site sudoers rule.")
    output.info(f"  Required drop-in {path}:")
    output.info(f"    {rule.strip()}")
    answer = input("Install this rule now (asks for your sudo password)? [y/N] ")
    if answer.strip().lower() not in ("y", "yes"):
        raise SudoersError("Sudoers setup declined.", recovery=_admin_recovery(site_name))

    _install_rule(rule, path, site_name)
    ensure_dev_versions_dir()

    if not probe(site_name):
        raise SudoersError(
            f"Sudoers rule installed at {path}, but running commands as "
            f"site user '{site_name}' still fails.",
            recovery=(
                f"Check for conflicting sudoers entries: sudo grep -r {get_real_user()} "
                f"/etc/sudoers /etc/sudoers.d/"
            ),
        )
    output.success(f"Sudoers rule installed: {path}")


def _install_rule(rule: str, path: Path, site_name: str) -> None:
    """Validate the rule with ``visudo -cf`` and install the drop-in as root."""
    _authenticate_sudo()
    with tempfile.NamedTemporaryFile("w", prefix="cmk-dev-deploy-sudoers-") as tmp:
        tmp.write(rule)
        tmp.flush()
        check = _run_root(["visudo", "-cf", tmp.name])
        if check.returncode != 0:
            raise SudoersError(
                "Generated sudoers rule failed visudo validation: "
                f"{check.stderr.strip() or check.stdout.strip()}",
                recovery=_admin_recovery(site_name),
            )
        result = _run_root(
            ["install", "-m", "0440", "-o", "root", "-g", "root", tmp.name, str(path)]
        )
        if result.returncode != 0:
            raise SudoersError(
                f"Failed to install sudoers drop-in {path}: {result.stderr.strip()}",
                recovery=_admin_recovery(site_name),
            )


def ensure_dev_versions_dir() -> None:
    """Ensure the deploy-user-owned clone base directory exists.

    Creating a directory under ``/omd`` requires root, so this may prompt
    for the sudo password — once per machine, ever.

    Raises:
        SudoersError: If the directory cannot be created.
    """
    if os.access(DEV_VERSIONS_DIR, os.W_OK):
        return
    user = get_real_user()
    output.info(f"Creating {DEV_VERSIONS_DIR} (owned by {user}) requires sudo")
    _authenticate_sudo()
    for cmd in (["mkdir", "-p", str(DEV_VERSIONS_DIR)], ["chown", user, str(DEV_VERSIONS_DIR)]):
        result = _run_root(cmd)
        if result.returncode != 0:
            raise SudoersError(
                f"Failed to prepare {DEV_VERSIONS_DIR}: {result.stderr.strip()}",
                recovery=(
                    "Ask an administrator to run:\n"
                    f"    sudo mkdir -p {DEV_VERSIONS_DIR}\n"
                    f"    sudo chown {user} {DEV_VERSIONS_DIR}"
                ),
            )


def print_setup(site_name: str) -> None:
    """Print the manual setup commands (``--print-setup``)."""
    output.info(
        f"Run these commands as an administrator to set up the clone backend "
        f"for site '{site_name}':"
    )
    print(admin_setup_commands(site_name))  # noqa: T201 -- raw stdout for copy-paste


def remove_setup(site_name: str) -> None:
    """Remove the per-site sudoers drop-in (``--remove-setup``).

    Raises:
        SudoersError: If the drop-in cannot be removed.
    """
    path = drop_in_path(site_name)
    if not path.exists() and not probe(site_name):
        output.info(f"No sudoers rule installed for site '{site_name}'.")
        return
    output.info(f"Removing sudoers drop-in {path} (asks for your sudo password)")
    _authenticate_sudo()
    result = _run_root(["rm", "-f", str(path)])
    if result.returncode != 0:
        raise SudoersError(f"Failed to remove {path}: {result.stderr.strip()}")
    output.success(f"Sudoers rule removed: {path}")


# ---------------------------------------------------------------------------
# Local root helpers (kept self-contained for the PATH-shim based tests)
# ---------------------------------------------------------------------------


def _authenticate_sudo() -> None:
    """Refresh the sudo timestamp, prompting on the terminal if needed."""
    env = {k: v for k, v in os.environ.items() if k != "SUDO_ASKPASS"}
    subprocess.run(
        ["sudo", "-v", "-p", "[cmk-dev-deploy] sudo password for %u: "],
        check=False,
        env=env,
    )


def _run_root(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a command as root, assuming :func:`_authenticate_sudo` ran before."""
    return subprocess.run(
        ["sudo", "-n", *cmd],
        capture_output=True,
        text=True,
        check=False,
        timeout=_SETUP_TIMEOUT,
    )
