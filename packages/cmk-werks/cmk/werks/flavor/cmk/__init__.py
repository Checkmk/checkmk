#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from cmk.werks.tool import parse_werk
from cmk.werks.tool.flavor import RepoFiles
from cmk.werks.tool.load import load_werk_model
from cmk.werks.tool.parse import WerkV2ParseResult

from . import collect, version
from .config import CmkConfig
from .models import WerkV2, WerkV3

V1_DEFAULTS: Mapping[str, str] = {"compatible": "compat", "edition": "cre"}


def load_werk(*, file_content: str, file_name: str) -> WerkV3:
    parsed = parse_werk(file_content, file_name, v1_defaults=V1_DEFAULTS)
    if isinstance(parsed, WerkV2ParseResult):
        return load_werk_model(WerkV2, parsed).to_werk()
    return load_werk_model(WerkV3, parsed)


class CmkFlavor:
    name: Literal["cmk"] = "cmk"
    config_model = CmkConfig
    v1_defaults = V1_DEFAULTS
    branch_regex = collect.BRANCH_REGEX
    version_regex = version.VERSION_REGEX

    def load_werk(self, *, file_content: str, file_name: str) -> WerkV3:
        return load_werk(file_content=file_content, file_name=file_name)

    def read_current_version(self, repo: RepoFiles) -> str | None:
        return version.read_current_version(repo)

    def cleanup_branch_name(self, branch_name: str) -> str:
        return collect.cleanup_branch_name(branch_name)

    def adapt_werk_string(self, werk_string: str, werk_id: int) -> str:
        return collect.adapt_werk_string(werk_string, werk_id)
