#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any, NamedTuple


class WerkV1ParseResult(NamedTuple):
    metadata: dict[str, str]
    description: list[str]


def parse_werk_v1(content: str, werk_id: int) -> WerkV1ParseResult:
    """
    parse werk v1 but do not validate, or transform description
    """
    werk: dict[str, Any] = {
        "compatible": "compat",
        "edition": "cre",
        "id": werk_id,
    }
    description = []
    in_header = True
    for line in content.split("\n"):
        if in_header and not line.strip():
            in_header = False
        elif in_header:
            key, text = line.split(":", 1)
            try:
                value: int | str = int(text.strip())
            except ValueError:
                value = text.strip()
            field = key.lower()
            werk[field] = value
        else:
            description.append(line)

    while description and description[-1] == "":
        description.pop()

    return WerkV1ParseResult(werk, description)
