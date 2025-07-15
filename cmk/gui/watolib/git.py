#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import glob
import os
import subprocess

from cmk.ccc.exceptions import MKGeneralException

import cmk.utils
import cmk.utils.paths

from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user


def add_message(message: str) -> None:
    _git_messages().append(message)


@request_memoize()
def _git_messages() -> list[str]:
    """Initializes the request global data structure and returns it"""
    return []


def do_git_commit() -> None:
    author = f"{user.id} <{user.email}>"
    if not os.path.exists(cmk.utils.paths.default_config_dir / ".git"):
        logger.debug("GIT: Initializing")
        _git_command(["init"])

        # Set git repo global user/mail. seems to be needed to prevent warning message
        # on at least ubuntu 15.04: "Please tell me who you are. Run git config ..."
        # The individual commits by users override the author on their own
        _git_command(["config", "user.email", "check_mk"])
        _git_command(["config", "user.name", "check_mk"])

        _write_gitignore_files()
        _git_add_files()
        _git_command(
            [
                "commit",
                "--untracked-files=no",
                "--author",
                author,
                "-m",
                _("Initialized GIT for Checkmk"),
            ]
        )

    if _git_has_pending_changes():
        logger.debug("GIT: Found pending changes - Update gitignore file")
        _write_gitignore_files()

    # Writing the gitignore files might have reverted the change. So better re-check.
    if _git_has_pending_changes():
        logger.debug("GIT: Still has pending changes")
        _git_add_files()

        message = ", ".join(_git_messages())
        if not message:
            message = _("Unknown configuration change")

        _git_command(["commit", "--author", author, "-F", "-"], stdin=message)


def _git_add_files() -> None:
    path_pattern = cmk.utils.paths.default_config_dir / "*.d/wato"
    rel_paths = [
        os.path.relpath(p, cmk.utils.paths.default_config_dir) for p in glob.glob(str(path_pattern))
    ]
    _git_command(["add", "--all", ".gitignore"] + rel_paths)


def _git_command(args: list[str], stdin: str | None = None) -> None:
    command = ["git"] + args
    debug_command = subprocess.list2cmdline(command)
    if stdin:
        if (len_stdin := len(stdin)) > 50:
            debug_command += f" < {stdin[:45]}[...] ({len_stdin} chars)"
        else:
            debug_command += f" < {stdin}"
    logger.debug(
        "GIT: Execute in %s: %s",
        cmk.utils.paths.default_config_dir,
        debug_command,
    )
    try:
        completed_process = subprocess.run(
            command,
            cwd=cmk.utils.paths.default_config_dir,
            input=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            check=False,
        )
    except (FileNotFoundError, UnicodeEncodeError) as e:
        raise MKGeneralException(
            _("Error executing GIT command <tt>%s</tt>:<br><br>%s") % (debug_command, e)
        ) from e

    if completed_process.returncode:
        raise MKGeneralException(
            _("Error executing GIT command <tt>%s</tt>:<br><br>%s")
            % (debug_command, completed_process.stdout.replace("\n", "<br>\n"))
        )


def _git_has_pending_changes() -> bool:
    try:
        completed_process = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cmk.utils.paths.default_config_dir,
            stdout=subprocess.PIPE,
            encoding="utf-8",
            check=False,
        )
        return bool(completed_process.stdout)
    except FileNotFoundError:
        return False  # ignore missing git command


# TODO: Use cmk.store
def _write_gitignore_files() -> None:
    """Make sure that .gitignore-files are present and up to date

    Only files below the "wato" directories should be under git control. The files in
    etc/check_mk/*.mk should not be put under control."""
    config_dir = cmk.utils.paths.default_config_dir

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
        )

    for subdir in config_dir.iterdir():
        if not subdir.name.endswith(".d"):
            continue

        with subdir.joinpath(".gitignore").open("w", encoding="utf-8") as f:
            f.write("*\n!wato\n")

        if subdir.joinpath("wato").exists():
            with subdir.joinpath("wato/.gitignore").open("w", encoding="utf-8") as f:
                f.write("!*\n")
