#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.product_usage.collectors.host_services as host_services_collector


@pytest.mark.parametrize(
    "services",
    [
        pytest.param(["Check_MK", "Check_MK Discovery"], id="both default services"),
        pytest.param(["Check_MK"], id="only Check_MK"),
        pytest.param(["Check_MK Discovery"], id="only Check_MK Discovery"),
        pytest.param([], id="no services"),
    ],
)
def test_host_with_default_services_only_is_counted(services: list[str]) -> None:
    count = host_services_collector.collect([services])

    assert count == 1


def test_host_with_any_other_service_is_not_counted() -> None:
    count = host_services_collector.collect([["Check_MK", "Check_MK Discovery", "CPU load"]])

    assert count == 0


def test_count_is_the_number_of_hosts_with_default_services_only() -> None:
    count = host_services_collector.collect(
        [["Check_MK", "Check_MK Discovery"], [], ["Check_MK", "CPU load"], ["PING"]]
    )

    assert count == 2


def test_host_with_the_legacy_discovery_service_is_not_counted() -> None:
    count = host_services_collector.collect([["Check_MK", "Check_MK inventory"]])

    assert count == 0
