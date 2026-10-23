#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from . import constants
from .convert import werkv1_to_werkv2
from .parse import parse_werk_v2, parse_werk_v3, WerkV2ParseResult, WerkV3ParseResult


def parse_werk(
    file_content: str, file_name: str, *, v1_defaults: Mapping[str, str]
) -> WerkV2ParseResult | WerkV3ParseResult:
    if file_name.endswith(".md"):
        if file_content.startswith(constants.WERK_V2_START):
            return parse_werk_v2(file_content, file_name.removesuffix(".md"))
        return parse_werk_v3(file_content, file_name.removesuffix(".md"))
    werk_id = int(file_name)
    return parse_werk_v2(werkv1_to_werkv2(file_content, werk_id, v1_defaults), str(werk_id))
