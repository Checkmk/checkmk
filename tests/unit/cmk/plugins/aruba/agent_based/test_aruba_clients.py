#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.agent_based.v3_unstable import Metric
from cmk.plugins.aruba.agent_based import aruba_clients


def test_no_data_is_no_section() -> None:
    assert aruba_clients.parse_aruba_clients([]) is None


def test_a_count_is_discovered() -> None:
    section = aruba_clients.parse_aruba_clients([["5"]])
    assert section is not None

    assert list(aruba_clients.check_plugin_aruba_clients.discovery_function(section)) == [Service()]


def test_a_count_is_reported_with_its_metric() -> None:
    section = aruba_clients.parse_aruba_clients([["5"]])
    assert section is not None

    results = list(aruba_clients.check_aruba_clients(section))

    assert results == [
        Result(state=State.OK, summary="Connections: 5"),
        Metric("connections", 5),
    ]


def test_an_unreadable_count_names_the_received_value() -> None:
    section = aruba_clients.parse_aruba_clients([[""]])
    assert section is not None

    results = list(aruba_clients.check_aruba_clients(section))

    assert [str(r) for r in results] == [
        "Could not parse 'wlsxSwitchTotalNumStationsAssociated': invalid literal for int() with base 10: ''"
    ]
