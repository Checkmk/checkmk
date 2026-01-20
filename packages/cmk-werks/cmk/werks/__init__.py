#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from .convert import werkv1_to_werkv2
from .load import load_werk_v2
from .models import Werk
from .parse import (
    parse_werk_v2,
    parse_werk_v3,
    WerkV2ParseResult,
    WerkV3ParseResult,
    WERK_V2_START,
)


def parse_werk(file_content: str, file_name: str) -> WerkV2ParseResult | WerkV3ParseResult:
    if file_name.endswith(".md"):
        if file_content.startswith(WERK_V2_START):
            return parse_werk_v2(file_content, file_name.removesuffix(".md"))
        return parse_werk_v3(file_content, file_name.removesuffix(".md"))
    file_content, werk_id = werkv1_to_werkv2(file_content, int(file_name))
    return parse_werk_v2(file_content, str(werk_id))  # TODO: str does not make sense!


def load_werk(*, file_content: str, file_name: str) -> Werk:
    parsed = parse_werk(file_content, file_name)
    return load_werk_v2(parsed)
