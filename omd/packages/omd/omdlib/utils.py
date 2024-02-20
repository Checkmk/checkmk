#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import enum
import os
import shutil
from collections.abc import Iterator
from pathlib import Path


def is_containerized() -> bool:
    return (
        os.path.exists("/.dockerenv")
        or os.path.exists("/run/.containerenv")
        or os.environ.get("CMK_CONTAINERIZED") == "TRUE"
    )


@contextlib.contextmanager
def chdir(path: str) -> Iterator[None]:
    """Change working directory and return on exit"""
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def delete_user_file(user_path: str) -> None:
    if not os.path.islink(user_path) and os.path.isdir(user_path):
        shutil.rmtree(user_path)
    else:
        os.remove(user_path)


def delete_directory_contents(d: str) -> None:
    for f in os.listdir(d):
        delete_user_file(d + "/" + f)


def omd_base_path() -> str:
    return "/"


def get_editor() -> str:
    alternative = os.environ.get("EDITOR", "/usr/bin/vi")
    editor = os.environ.get("VISUAL", alternative)

    if not os.path.exists(editor):
        return "vi"

    return editor


class SiteDistributedSetup(str, enum.Enum):
    DISTRIBUTED_REMOTE = "distributed_remote"
    NOT_DISTRIBUTED = "not_distributed"
    UNKNOWN = "unknown"


def get_site_distributed_setup() -> SiteDistributedSetup:
    file_vars: dict = {}
    if (distr_wato_filepath := Path("~/etc/omd/distributed.mk").expanduser()).exists():
        exec(  # nosec B102 # BNS:aee528
            distr_wato_filepath.read_text(),
            file_vars,
            file_vars,
        )
    if "is_wato_remote_site" not in file_vars:
        return SiteDistributedSetup.UNKNOWN
    if file_vars["is_wato_remote_site"] is True:
        return SiteDistributedSetup.DISTRIBUTED_REMOTE
    return SiteDistributedSetup.NOT_DISTRIBUTED
