#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Mapping

from cmk.base.plugins.agent_based.agent_based_api.v1 import register
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


@dataclasses.dataclass(frozen=True)
class _ElasticIndex:
    count: float
    size: float


_Section = Mapping[str, _ElasticIndex]


def parse_elasticsearch_indices(string_table: StringTable) -> _Section:
    return {
        index_name: _ElasticIndex(float(count_str), float(count_size))
        for (index_name, count_str, count_size) in string_table
    }


register.agent_section(
    name="elasticsearch_indices",
    parse_function=parse_elasticsearch_indices,
)
