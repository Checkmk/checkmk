#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import glob
import os
import subprocess
from pathlib import Path
from typing import List

import cmk.utils
import cmk.utils.paths

from cmk.gui.exceptions import MKGeneralException
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.utils.logged_in import user


def add_message(message: str) -> None:
    _git_messages().append(message)


@request_memoize()
def _git_messages() -> List[str]:
    """Initializes the request global data structure and returns it"""
    return []


def do_git_commit() -> None:
    author = "%s <%s>" % (user.id, user.email)
    git_dir = cmk.utils.paths.default_config_dir + "/.git"
    if not os.path.exists(git_dir):
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

        _git_command(["commit", "--author", author, "-m", message])


def _git_add_files() -> None:
    path_pattern = os.path.join(cmk.utils.paths.default_config_dir, "*.d/wato")
    rel_paths = [
        os.path.relpath(p, cmk.utils.paths.default_config_dir) for p in glob.glob(path_pattern)
    ]
    _git_command(["add", "--all", ".gitignore"] + rel_paths)


def _git_command(args: List[str]) -> None:
    command = ["git"] + args
    logger.debug(
        "GIT: Execute in %s: %s",
        cmk.utils.paths.default_config_dir,
        subprocess.list2cmdline(command),
    )
    try:
        completed_process = subprocess.run(
            command,
            cwd=cmk.utils.paths.default_config_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            check=False,
        )
    except OSError as e:
        if e.errno == errno.ENOENT:
            raise MKGeneralException(
                _("Error executing GIT command <tt>%s</tt>:<br><br>%s")
                % (subprocess.list2cmdline(command), e)
            )
        raise

    if completed_process.returncode:
        raise MKGeneralException(
            _("Error executing GIT command <tt>%s</tt>:<br><br>%s")
            % (subprocess.list2cmdline(command), completed_process.stdout.replace("\n", "<br>\n"))
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
    except OSError as e:
        if e.errno == errno.ENOENT:
            return False  # ignore missing git command
        raise


# TODO: Use cmk.store
def _write_gitignore_files() -> None:
    """Make sure that .gitignore-files are present and up to date

    Only files below the "wato" directories should be under git control. The files in
    etc/check_mk/*.mk should not be put under control."""
    config_dir = Path(cmk.utils.paths.default_config_dir)

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
