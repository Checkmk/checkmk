#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io

from cmk.werks.tool.config import try_load_version_from_defines_make_content
from cmk.werks.tool.flavor import read_repo_file, RepoFiles


def version_from_defines_make(content: bytes) -> str | None:
    return try_load_version_from_defines_make_content(io.BytesIO(content))


def read_current_version(repo: RepoFiles) -> str | None:
    if (content := read_repo_file(repo, "defines.make")) is None:
        return None
    return version_from_defines_make(content)
