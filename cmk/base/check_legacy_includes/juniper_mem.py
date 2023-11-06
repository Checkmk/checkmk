#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from cmk.base.check_legacy_includes.mem import check_memory_element


@dataclass(frozen=True)
class Section:
    used: int
    total: int


def discover_juniper_mem_generic(section: Section) -> Iterator[tuple[None, dict]]:
    yield None, {}


def check_juniper_mem_generic(
    _no_item: None,
    params: Mapping[str, Any],
    section: Section,
) -> tuple[int, str, list]:
    return check_memory_element(
        label="Used",
        used=section.used,
        total=section.total,
        levels=params["levels"],
        metric_name="mem_used",
    )
