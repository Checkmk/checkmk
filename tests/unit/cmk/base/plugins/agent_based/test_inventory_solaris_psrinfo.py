#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable, NamedTuple, Optional, TypeVar

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.inventory_solaris_psrinfo import (
    inventory_solaris_cpus,
    parse_solaris_psrinfo_physical,
    parse_solaris_psrinfo_table,
    parse_solaris_psrinfo_verbose,
    parse_solaris_psrinfo_virtual,
)

from .utils_inventory import sort_inventory_result

T = TypeVar("T")


class PsrInfo(NamedTuple):
    psrinfo: str
    psrinfo_pv: str
    psrinfo_p: str
    psrinfo_t: Optional[str]


test_set_1 = PsrInfo(
    psrinfo=(
        "0       on-line     since       04/01/2022 00:00:00\n"
        "1       on-line     since       04/01/2022 00:00:00\n"
        "2       on-line     since       04/01/2022 00:00:00\n"
        "3       on-line     since       04/01/2022 00:00:00\n"
        "4       on-line     since       04/01/2022 00:00:00\n"
        "5       on-line     since       04/01/2022 00:00:00\n"
        "6       on-line     since       04/01/2022 00:00:00\n"
        "7       on-line     since       04/01/2022 00:00:00\n"
        "8       on-line     since       04/01/2022 00:00:00\n"
        "9       on-line     since       04/01/2022 00:00:00\n"
        "10      on-line     since       04/01/2022 00:00:00\n"
        "11      on-line     since       04/01/2022 00:00:00\n"
        "12      on-line     since       04/01/2022 00:00:00\n"
        "13      on-line     since       04/01/2022 00:00:00\n"
        "14      on-line     since       04/01/2022 00:00:00\n"
        "15      on-line     since       04/01/2022 00:00:00\n"
        "16      on-line     since       04/01/2022 00:00:00\n"
        "17      on-line     since       04/01/2022 00:00:00\n"
        "18      on-line     since       04/01/2022 00:00:00\n"
        "19      on-line     since       04/01/2022 00:00:00\n"
        "20      on-line     since       04/01/2022 00:00:00\n"
        "21      on-line     since       04/01/2022 00:00:00\n"
        "22      on-line     since       04/01/2022 00:00:00\n"
        "23      on-line     since       04/01/2022 00:00:00\n"
        "56      on-line     since       04/01/2022 00:00:00\n"
        "57      on-line     since       04/01/2022 00:00:00\n"
        "58      on-line     since       04/01/2022 00:00:00\n"
        "59      on-line     since       04/01/2022 00:00:00\n"
        "60      on-line     since       04/01/2022 00:00:00\n"
        "61      on-line     since       04/01/2022 00:00:00\n"
        "62      on-line     since       04/01/2022 00:00:00\n"
        "63      on-line     since       04/01/2022 00:00:00\n"
    ),
    psrinfo_pv=(
        "The physical processor has 3 cores and 24 virtual processors (0-15,56-63)\n"
        "  The core has 8 virtual processors (56-63)\n"
        "  The core has 8 virtual processors (0-7)\n"
        "  The core has 8 virtual processors (8-15)\n"
        "    SPARC-S7 (chipid 0, clock 4267 MHz)\n"
        "The physical processor has 1 core and 8 virtual processors (16-23)\n"
        "  The core has 8 virtual processors (16-23)\n"
        "    SPARC-S7 (chipid 0, clock 4267 MHz)\n"
    ),
    psrinfo_p="2\n",
    psrinfo_t=(
        "socket: 0\n"
        "  core: 0\n"
        "    cpus: 56-63\n"
        "  core: 1\n"
        "    cpus: 0-7\n"
        "  core: 2\n"
        "    cpus: 8-15\n"
        "socket: 1\n"
        "  core: 3\n"
        "    cpus: 16-23\n"
    ),
)

test_set_2 = PsrInfo(
    psrinfo=(
        "0       on-line     since       04/01/2022 00:00:00\n"
        "1       on-line     since       04/01/2022 00:00:00\n"
        "2       on-line     since       04/01/2022 00:00:00\n"
        "3       on-line     since       04/01/2022 00:00:00\n"
        "4       on-line     since       04/01/2022 00:00:00\n"
        "5       on-line     since       04/01/2022 00:00:00\n"
        "6       on-line     since       04/01/2022 00:00:00\n"
        "7       on-line     since       04/01/2022 00:00:00\n"
        "8       on-line     since       04/01/2022 00:00:00\n"
        "9       on-line     since       04/01/2022 00:00:00\n"
        "10      on-line     since       04/01/2022 00:00:00\n"
        "11      on-line     since       04/01/2022 00:00:00\n"
        "12      on-line     since       04/01/2022 00:00:00\n"
        "13      on-line     since       04/01/2022 00:00:00\n"
        "14      on-line     since       04/01/2022 00:00:00\n"
        "15      on-line     since       04/01/2022 00:00:00\n"
    ),
    psrinfo_pv=(
        "The physical processor has 16 virtual processors (0-15)\n"
        "  SPARC-T5 (chipid 0, clock 3600 MHz)\n"
    ),
    psrinfo_p="2\n",
    psrinfo_t=None,
)


def _section(
    section_function: Callable[[StringTable], T], agent_output: Optional[str]
) -> Optional[T]:
    if agent_output is None:
        return None

    return section_function([line.split() for line in agent_output.splitlines()])


@pytest.mark.parametrize(
    "test_set, expected_result",
    [
        (
            test_set_1,
            [
                Attributes(
                    path=["hardware", "cpu"],
                    inventory_attributes={
                        "cpus": 2,
                        "cores": 4,
                        "threads": 32,
                        "Model": "SPARC-S7",
                        "Maximum Speed": "4267 MHz",
                    },
                ),
            ],
        ),
        (
            PsrInfo(
                psrinfo=test_set_1.psrinfo,
                psrinfo_pv=test_set_1.psrinfo_pv,
                psrinfo_p=test_set_1.psrinfo_p,
                psrinfo_t=None,
            ),
            [
                Attributes(
                    path=["hardware", "cpu"],
                    inventory_attributes={
                        "cpus": 2,
                        "cores": 4,
                        "threads": 32,
                        "Model": "SPARC-S7",
                        "Maximum Speed": "4267 MHz",
                    },
                ),
            ],
        ),
        (
            test_set_2,
            [
                Attributes(
                    path=["hardware", "cpu"],
                    inventory_attributes={
                        "cpus": 2,
                        "cores": 2,
                        "threads": 16,
                        "Model": "SPARC-T5",
                        "Maximum Speed": "3600 MHz",
                    },
                ),
            ],
        ),
    ],
)
def test_inventory_solaris_cpus(test_set, expected_result) -> None:
    assert sort_inventory_result(
        inventory_solaris_cpus(
            _section(parse_solaris_psrinfo_physical, test_set.psrinfo_p),
            _section(parse_solaris_psrinfo_virtual, test_set.psrinfo),
            _section(parse_solaris_psrinfo_verbose, test_set.psrinfo_pv),
            _section(parse_solaris_psrinfo_table, test_set.psrinfo_t),
        )
    ) == sort_inventory_result(expected_result)
