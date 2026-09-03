#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from collections.abc import Mapping
from pathlib import Path

import cmk.utils.paths
from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user

# The .gitignore contents of the Setup managed directories below etc/check_mk/*.d. Each of them
# needs its own file, because a "*" in a parent .gitignore also matches in nested directories.
_TRACKED_SUBDIRS: Mapping[str, str] = {
    # Everything, this holds subfolders and non-.mk files such as bi_config.bi.
    "wato": "!*\n*swp\n*.mk.new\n*.pkl\n",
    # Only the exported rule packs, which are always named <rule pack id>.mk. Writing a .gitignore
    # into rule_packs itself would make the MKP tool report it as an unpackaged rule pack file.
    "mkp": "*\n!rule_packs\n!rule_packs/*.mk\n",
}

# Files below etc/check_mk/*.d that are written by "omd config" instead of Setup. See HOOK_RELPATHS
# in omdlib/update.py. Anchored, so that same-named files in the tracked subdirectories remain.
_OMD_HOOK_FILES = ("microcore.mk", "mkeventd.mk", "pnp4nagios.mk", "liveproxyd.mk")


def add_message(message: str) -> None:
    _git_messages().append(message)


@request_memoize()
def _git_messages() -> list[str]:
    """Initializes the request global data structure and returns it"""
    return []


def do_git_commit() -> None:
    author = f"{user.id} <{user.email}>"
    config_dir = cmk.utils.paths.default_config_dir
    if not (config_dir / ".git").exists():
        logger.debug("GIT: Initializing")
        _git_command(["init"], config_dir)

        # Set git repo global user/mail. seems to be needed to prevent warning message
        # on at least ubuntu 15.04: "Please tell me who you are. Run git config ..."
        # The individual commits by users override the author on their own
        _git_command(["config", "user.email", "check_mk"], config_dir)
        _git_command(["config", "user.name", "check_mk"], config_dir)

        _write_gitignore_files(config_dir)
        _git_add_files(config_dir)
        _git_command(
            [
                "commit",
                "--untracked-files=no",
                "--author",
                author,
                "-m",
                _("Initialized GIT for Checkmk"),
            ],
            config_dir,
        )

    if _git_has_pending_changes(config_dir):
        logger.debug("GIT: Found pending changes - Update gitignore file")
        _write_gitignore_files(config_dir)

    # Writing the gitignore files might have reverted the change. So better re-check.
    if _git_has_pending_changes(config_dir):
        logger.debug("GIT: Still has pending changes")
        _git_add_files(config_dir)

        message = ", ".join(_git_messages())
        if not message:
            message = _("Unknown configuration change")

        _git_command(["commit", "--author", author, "-F", "-"], config_dir, stdin=message)


def _git_add_files(config_dir: Path) -> None:
    # The .gitignore files decide what is added below the *.d directories.
    subdirs = sorted(p.name for p in config_dir.iterdir() if p.name.endswith(".d"))
    _git_command(["add", "--all", ".gitignore", *subdirs], config_dir)


def _git_command(args: list[str], config_dir: Path, stdin: str | None = None) -> None:
    command = ["git"] + args
    debug_command = subprocess.list2cmdline(command)
    if stdin:
        if (len_stdin := len(stdin)) > 50:
            debug_command += f" < {stdin[:45]}[...] ({len_stdin} chars)"
        else:
            debug_command += f" < {stdin}"
    logger.debug(
        "GIT: Execute in %(config_dir)s: %(command)s",
        {"config_dir": config_dir, "command": debug_command},
    )
    try:
        completed_process = subprocess.run(
            command,
            cwd=config_dir,
            input=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            check=False,
        )
    except (FileNotFoundError, UnicodeEncodeError) as e:
        raise MKGeneralException(
            _("Error executing GIT command <tt>%(debug_command)s</tt>:<br><br>%(e)s")
            % {"debug_command": debug_command, "e": e}
        ) from e

    if completed_process.returncode:
        raise MKGeneralException(
            _("Error executing GIT command <tt>%(debug_command)s</tt>:<br><br>%(output)s")
            % {
                "debug_command": debug_command,
                "output": completed_process.stdout.replace("\n", "<br>\n"),
            }
        )


def _git_has_pending_changes(config_dir: Path) -> bool:
    try:
        completed_process = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=config_dir,
            stdout=subprocess.PIPE,
            encoding="utf-8",
            check=False,
        )
        return bool(completed_process.stdout)
    except FileNotFoundError:
        return False  # ignore missing git command


# TODO: Use cmk.store
def _write_gitignore_files(config_dir: Path) -> None:
    """Make sure that .gitignore-files are present and up to date

    Only the Setup managed configuration below etc/check_mk/*.d should be under git control. The
    generated files in etc/check_mk/*.mk should not be put under control."""
    with config_dir.joinpath(".gitignore").open("w", encoding="utf-8") as f:
        f.write(
            "# This file is under control of Checkmk. Please don't modify it.\n"
            "# Your changes will be overwritten.\n"
            "\n"
            "*\n"
            "!*.d\n"
            "!.gitignore\n"
            "*swp\n"
            "*.mk.new\n"
            "*.pkl\n"
        )

    subdir_content = (
        "*\n!*.mk\n"
        + "".join(f"!{name}\n" for name in _TRACKED_SUBDIRS)
        + "".join(f"/{name}\n" for name in _OMD_HOOK_FILES)
    )
    for subdir in config_dir.iterdir():
        if not subdir.name.endswith(".d"):
            continue

        with subdir.joinpath(".gitignore").open("w", encoding="utf-8") as f:
            f.write(subdir_content)

        for name, content in _TRACKED_SUBDIRS.items():
            if (tracked := subdir / name).exists():
                with tracked.joinpath(".gitignore").open("w", encoding="utf-8") as f:
                    f.write(content)
