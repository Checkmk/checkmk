#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import SectionName


@pytest.mark.parametrize(
    "info, expected_parsed",
    [
        (
            [
                [["1", "1", "1", "1"], ["2", "0", "0", "0"]],
                [["1", "CPU of Module 1"], ["2", "CPU of Module 2"]],
            ],
            {"of Module 1": {"mem_free": 1.0, "mem_reserved": 1.0, "mem_used": 1.0}},
        )
    ],
)
def test_parse_cisco_cpu_memory_multiitem(
    fix_register: FixRegister, info: Sequence[Sequence[str]], expected_parsed: Mapping[str, Any]
) -> None:
    section_plugin = fix_register.snmp_sections[SectionName("cisco_cpu_memory")]
    result = section_plugin.parse_function(info)
    assert result == expected_parsed
