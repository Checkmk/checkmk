#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.werks.tool.flavor import read_repo_file, RepoFiles

VERSION_REGEX = r"^\d.\d.\d([ipb]\d+)?$"


def version_from_defines_make(content: bytes) -> str | None:
    for line in content.splitlines():
        if line.startswith(b"VERSION"):
            return line.split(b"=", 1)[1].strip().decode("utf-8")
    return None


def read_current_version(repo: RepoFiles) -> str | None:
    if (content := read_repo_file(repo, "defines.make")) is None:
        return None
    return version_from_defines_make(content)
