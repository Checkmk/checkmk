#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Result, State
from cmk.plugins.collection.agent_based import prometheus_build


def test_check_prometheus_build() -> None:
    assert list(
        prometheus_build.check_prometheus_build(
            {
                "version": ["2.0.0"],
                "scrape_target": {"targets_number": 8, "down_targets": ["minikube", "node"]},
                "reload_config_status": True,
            }
        )
    ) == [
        Result(
            state=State.OK,
            summary="Version: 2.0.0",
        ),
        Result(
            state=State.OK,
            summary="Config reload: Success",
        ),
        Result(
            state=State.WARN,
            summary="Scrape Targets in up state: 6 out of 8",
            details="Scrape Targets in up state: 6 out of 8 (Targets in down state: minikube, node)",
        ),
    ]


def test_check_prometheus_build_with_multiple_versions() -> None:
    assert list(
        prometheus_build.check_prometheus_build(
            {
                "version": ["2.0.0", "2.14.0"],
            }
        )
    ) == [
        Result(
            state=State.OK,
            summary="Version: multiple instances",
            details="Versions: 2.0.0, 2.14.0",
        ),
    ]
