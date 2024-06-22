#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.liebert.agent_based.lib import Section
from cmk.plugins.liebert.agent_based.liebert_compressor import (
    check_plugin_liebert_compressor,
    snmp_section_liebert_compressor,
)


def _section() -> Section:
    assert (
        section := snmp_section_liebert_compressor.parse_function(
            [
                [
                    [
                        "Compressor Head Pressure",
                        "5.9",
                        "bar",
                    ],
                    [
                        "Compressor Head Pressure",
                        "6.1",
                        "bar",
                    ],
                    [
                        "Compressor Head Pressure",
                        "Unavailable",
                        "bar",
                    ],
                    [
                        "Compressor Head Pressure",
                        "0.0",
                        "bar",
                    ],
                ]
            ]
        )
    ) is not None
    return section


def test_discovery() -> None:
    assert list(check_plugin_liebert_compressor.discovery_function(_section())) == [
        Service(item="Compressor Head Pressure"),
        Service(item="Compressor Head Pressure 2"),
        Service(item="Compressor Head Pressure 4"),
    ]


def test_check_ok() -> None:
    assert list(
        check_plugin_liebert_compressor.check_function(
            "Compressor Head Pressure 2", {"levels": (8, 12)}, _section()
        )
    ) == [
        Result(state=State.OK, summary="Head pressure: 6.10 bar"),
    ]
