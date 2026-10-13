#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.werks.tool.flavor import RepoFiles

from . import collect, version


class CmkFlavor:
    name: Literal["cmk"] = "cmk"
    branch_regex = collect.BRANCH_REGEX
    version_regex = version.VERSION_REGEX

    def read_current_version(self, repo: RepoFiles) -> str | None:
        return version.read_current_version(repo)

    def cleanup_branch_name(self, branch_name: str) -> str:
        return collect.cleanup_branch_name(branch_name)

    def adapt_werk_string(self, werk_string: str, werk_id: int) -> str:
        return collect.adapt_werk_string(werk_string, werk_id)
