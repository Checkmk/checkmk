#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Consolidated helper functions for interacting with the repository.

The functions in this module are designed with caching where appropriate to optimize performance.
They almost all require a Git repository to be present.
"""

import logging
import os
import subprocess
import sys
from collections.abc import Callable
from contextlib import suppress
from functools import cache
from pathlib import Path

LOGGER = logging.getLogger(__name__)


@cache
def repo_path() -> Path:
    """Returns the checkout/worktree path (in contrast to the 'git-dir')
    same as result of `git rev-parse --show-toplevel`, but repo_path is being executed
    quite often, so we take the not-so-portable-but-more-efficient approach.
    """
    return Path(__file__).resolve().parent.parent.parent.parent


def is_enterprise_repo() -> bool:
    return (repo_path() / "omd" / "packages" / "enterprise").exists()


def is_managed_repo() -> bool:
    return (repo_path() / "omd" / "packages" / "managed").exists()


def is_cloud_repo() -> bool:
    return (repo_path() / "omd" / "packages" / "cloud").exists()


def is_saas_repo() -> bool:
    return (repo_path() / "omd" / "packages" / "saas").exists()


def add_python_paths() -> None:
    sys.path.insert(0, str(repo_path()))
    if is_enterprise_repo():
        sys.path.insert(0, os.path.join(repo_path(), "non-free", "packages", "cmk-update-agent"))
    sys.path.insert(0, os.path.join(repo_path(), "omd/packages/omd"))


def add_protocols_path():
    sys.path.insert(0, str(repo_path()))
    if is_enterprise_repo():
        sys.path.insert(0, os.path.join(repo_path(), "non-free", "packages", "cmc-protocols"))


def add_otel_collector_path() -> None:
    sys.path.insert(0, str(repo_path()))
    if is_cloud_repo() or is_managed_repo():
        sys.path.insert(0, os.path.join(repo_path(), "non-free", "packages", "cmk-otel-collector"))


@cache
def qa_test_data_path() -> Path:
    return Path(__file__).parent.parent.parent.resolve() / Path("qa-test-data")


@cache
def branch_from_env(*, env_var: str, fallback: str | Callable[[], str] | None = None) -> str:
    if branch := os.environ.get(env_var):
        return branch
    if fallback:
        return fallback() if callable(fallback) else fallback
    raise RuntimeError(f"{env_var} environment variable, e.g. master, is missing")


@cache
def current_branch_version() -> str:
    return subprocess.check_output(
        [
            "make",
            "--no-print-directory",
            "-f",
            str(repo_path() / "defines.make"),
            "print-BRANCH_VERSION",
        ],
        encoding="utf-8",
    ).strip()


@cache
def branch_name_is_branch_version() -> bool:
    return (
        subprocess.check_output(
            [
                "make",
                "--no-print-directory",
                "-f",
                str(repo_path() / "defines.make"),
                "print-BRANCH_NAME_IS_BRANCH_VERSION",
            ],
            encoding="utf-8",
        ).strip()
        == "yes"
    )


@cache
def current_base_branch_name() -> str:
    if branch_name_is_branch_version():
        return current_branch_version()
    return "master"


@cache
def current_branch_name(default: str = "no-branch") -> str:
    try:
        branch_name = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            encoding="utf-8",
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return default

    return branch_name.split("\n", 1)[0]


@cache
def git_commit_id(path: Path | str) -> str:
    """Returns the git hash for given @path."""
    return subprocess.check_output(
        # use the full hash - short hashes cannot be checked out and they are not
        # unique among machines
        ["git", "log", "--pretty=tformat:%H", "-n1"] + [str(path)],
        cwd=repo_path(),
        text=True,
    ).strip("\n")


@cache
def git_essential_directories(checkout_dir: Path) -> list[str]:
    """Returns paths to all directories needed to be accessible in order to run git operations
    Note that if a directory is a subdirectory of checkout_dir it will be skipped"""

    essential_dirs = []
    # path to the 'real git repository directory', i.e. the common dir when dealing with work trees
    common_dir = (
        (
            checkout_dir
            / subprocess.check_output(
                ["git", "rev-parse", "--git-common-dir"], cwd=checkout_dir, text=True
            ).rstrip("\n")
        )
        .resolve()
        .absolute()
    )

    if not common_dir.is_relative_to(checkout_dir):
        essential_dirs.append(common_dir.as_posix())

    # In case of reference clones we also need to access them.
    # Not sure if 'objects/info/alternates' can contain more than one line and if we really need
    # the parent, but at least this one is working for us
    with suppress(FileNotFoundError):
        with (common_dir / "objects/info/alternates").open() as alternates:
            for alternate in (Path(line).parent for line in alternates):
                if not alternate.is_relative_to(checkout_dir):
                    essential_dirs.append(alternate.as_posix())

    return essential_dirs


@cache
def find_git_rm_mv_files(dirpath: Path) -> list[str]:
    """lists all files that have been deleted or renamed in the git repository below dirpath

    Args:
        dirpath (Path): Path to search for (relative to root of git repository)

    Returns:
        list[str]: list of detected files
    """
    del_files = []

    out = subprocess.check_output(
        [
            "git",
            "-C",
            str(dirpath),
            "status",
            str(dirpath),
        ],
        encoding="utf-8",
    ).split("\n")

    for line in out:
        if "deleted:" in line or "renamed:" in line:
            # Ignore files in subdirs of dirpath
            if line.split(dirpath.name)[1].count("/") > 1:
                continue

            filename = line.split("/")[-1]
            del_files.append(filename)
    return del_files
