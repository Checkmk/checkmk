#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from pytest import MonkeyPatch

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.prism_alerts import check_prism_alerts, discovery_prism_alerts

SECTION = [
    {
        "vm_name": "SRV-APP-01",
        "vm_id": "0000-0000",
        "arithmos_id": "0000-0000",
        "ncc_version": "4.6.0.1-e24121c6",
        "nos_version": "5.20.4.6",
        "vm_uuid": "0000-0000",
        "timestamp": 1665065787989551,
        "severity": "kInfo",
        "message": "It is recommended that NGT on the VM SRV-APP-01 with uuid 0000-0000 should be upgraded to the latest version supported by the cluster.NGT update contains bug fixes and improvements, which will improve the overall product experience.",
    },
    {
        "vm_name": "SRV-SQL-02",
        "vm_id": "0000-0000",
        "arithmos_id": "0000-0000",
        "ncc_version": "4.6.0.1-e24121c6",
        "nos_version": "5.20.4.6",
        "vm_uuid": "0000-0000",
        "timestamp": 1665065787957263,
        "severity": "kInfo",
        "message": "It is recommended that NGT on the VM SRV-SQL-02 with uuid 0000-0000 should be upgraded to the latest version supported by the cluster.NGT update contains bug fixes and improvements, which will improve the overall product experience.",
    },
]


@pytest.mark.parametrize(
    ["section", "expected_discovery_result"],
    [
        pytest.param(
            SECTION,
            [Service()],
            id="If data is available, a Service is discovered.",
        ),
        pytest.param(
            {},
            [Service()],
            id="If there are is no data (no error), Service is also discovered.",
        ),
    ],
)
def test_discovery_prism_alerts(
    section: Sequence[Mapping[Any, Any]],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discovery_prism_alerts(section)) == expected_discovery_result


@pytest.mark.parametrize(
    ["params", "section", "expected_check_result"],
    [
        pytest.param(
            {
                "prism_central_only": False,
            },
            SECTION,
            [
                Result(state=State.OK, summary="2 alerts"),
                Result(
                    state=State.OK,
                    summary="Last worst on Oct 06 2022 14:16:27: 'It is recommended that NGT on the VM SRV-APP-01 with uuid 0000-0000 should be upgraded to the latest version supported by the cluster.NGT update contains bug fixes and improvements, which will improve the overall product experience.'",
                ),
                Result(state=State.OK, notice="\nLast 10 Alerts\n"),
                Result(
                    state=State.OK,
                    notice="Oct 06 2022 14:16:27\tIt is recommended that NGT on the VM SRV-APP-01 with uuid 0000-0000 should be upgraded to the latest version supported by the cluster.NGT update contains bug fixes and improvements, which will improve the overall product experience.",
                ),
                Result(
                    state=State.OK,
                    notice="Oct 06 2022 14:16:27\tIt is recommended that NGT on the VM SRV-SQL-02 with uuid 0000-0000 should be upgraded to the latest version supported by the cluster.NGT update contains bug fixes and improvements, which will improve the overall product experience.",
                ),
            ],
            id="If the disk is in expected mount state and healthy, the check result is OK.",
        ),
    ],
)
def test_check_prism_alerts(
    params: Mapping[str, str],
    section: Sequence[Mapping[Any, Any]],
    expected_check_result: Sequence[Result],
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(time, "localtime", time.gmtime)
    assert (
        list(
            check_prism_alerts(
                params=params,
                section=section,
            )
        )
        == expected_check_result
    )
