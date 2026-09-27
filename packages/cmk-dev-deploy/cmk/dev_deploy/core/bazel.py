# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Bazel command composition for the dedicated deploy server.

Bazel executes one command at a time per output base.  On the checkout's
default server every deploy would queue behind (and block) the
developer's own bazel commands, so cmk-dev-deploy runs its Bazel commands
against a dedicated output base: a second server on the same workspace,
reading the same ``.bazelrc`` chain.  The shared disk cache keeps the
rebuild cost of the second output base low, and because the deploy server
only ever sees the site edition's configuration, its analysis cache is
never discarded by configuration flips.

Opting out (``--shared-bazel-server`` or ``CDD_SHARED_BAZEL_SERVER=1``)
restores the old single-server behavior, e.g. when disk space is tight.
"""

import hashlib
import os
from collections.abc import Sequence
from pathlib import Path

OUTPUT_BASE_ENV = "CDD_BAZEL_OUTPUT_BASE"
"""Environment override for the deploy server's output base path."""

SHARED_SERVER_ENV = "CDD_SHARED_BAZEL_SERVER"
"""Set to a non-empty value (other than ``0``) to use the default server."""

# Checkmk's analysis graph needs ~3g; bound the second server's JVM so it
# stays predictable next to the developer's main server.
_STARTUP_OPTIONS: tuple[str, ...] = ("--host_jvm_args=-Xmx3g",)

# Commands that (re)point the workspace convenience symlinks (bazel-bin,
# bazel-out, ...).  The deploy server must not flip them to its own output
# base under the developer's feet; the tool resolves artifact paths via
# ``bazel info`` and ``bazel cquery`` instead of the symlinks.
# A "/" symlink prefix means "create no symlinks".  The equivalent
# ``--experimental_convenience_symlinks=ignore`` cannot be used: the Aspect
# CLI wrapper mirrors that flag as a boolean and rejects the enum value.
_SYMLINK_CREATING_COMMANDS = frozenset({"build", "run", "test"})
_NO_SYMLINKS_OPTION = "--symlink_prefix=/"

# The tool copies top-level outputs out of bazel-out.  A user rc with
# ``--remote_download_outputs=minimal`` leaves cache hits unmaterialized
# (e.g. an empty Vue dist when switching back to an already built commit).
_DOWNLOADING_COMMANDS = frozenset({"build", "run"})
_DOWNLOAD_OPTION = "--remote_download_outputs=toplevel"


def use_shared_server() -> bool:
    """Return True when the user opted out of the dedicated deploy server."""
    return os.environ.get(SHARED_SERVER_ENV, "") not in ("", "0")


def request_shared_server() -> None:
    """Record the ``--shared-bazel-server`` opt-out for all later bazel calls.

    Stored in the environment so every module (including the crash-path
    diagnostics, which has no access to parsed CLI args) and every spawned
    subprocess sees the same mode.
    """
    os.environ[SHARED_SERVER_ENV] = "1"


def _checkout_digest(repo_root: Path) -> str:
    return hashlib.md5(str(repo_root.resolve()).encode(), usedforsecurity=False).hexdigest()


def _cache_dir() -> Path:
    cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return cache / "cmk-dev-deploy"


def deploy_output_base(repo_root: Path) -> Path:
    """Return the per-checkout output base of the deploy server."""
    if override := os.environ.get(OUTPUT_BASE_ENV):
        return Path(override)
    return _cache_dir() / "bazel" / _checkout_digest(repo_root)


def startup_options(repo_root: Path) -> list[str]:
    """Return the startup options selecting the deploy server; none for the shared server."""
    if use_shared_server():
        return []
    return [f"--output_base={deploy_output_base(repo_root)}", *_STARTUP_OPTIONS]


def command_options(command: str) -> list[str]:
    """Return the options the tool adds after *command*.

    Unless the shared server was requested, commands that would create
    convenience symlinks create none.  Building commands always materialize
    their top-level outputs.
    """
    download_options = [_DOWNLOAD_OPTION] if command in _DOWNLOADING_COMMANDS else []
    if use_shared_server():
        return download_options
    symlink_options = [_NO_SYMLINKS_OPTION] if command in _SYMLINK_CREATING_COMMANDS else []
    return [*symlink_options, *download_options]


def bazel_command(args: Sequence[str], repo_root: Path) -> list[str]:
    """Return the full bazel argv for *args* (e.g. ``["build", "//pkg:t"]``)."""
    command, *rest = args
    return ["bazel", *startup_options(repo_root), command, *command_options(command), *rest]
