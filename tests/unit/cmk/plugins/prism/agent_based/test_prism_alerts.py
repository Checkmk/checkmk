#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import time
from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from pytest import MonkeyPatch

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.prism.agent_based.prism_alerts import (
    check_prism_alerts,
    discovery_prism_alerts,
    parse_prism_alerts,
)

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


def test_newline_in_message(
    monkeypatch: MonkeyPatch,
) -> None:
    data = {
        "entities": [
            {
                "acknowledged": False,
                "acknowledged_by_username": "",
                "acknowledged_time_stamp_in_usecs": 0,
                "affected_entities": [
                    {
                        "entity_name": "blabla.com",
                        "entity_type": "cluster",
                        "entity_type_display_name": "cluster",
                        "id": "",
                        "uuid": "1234",
                    }
                ],
                "alert_details": None,
                "alert_title": "Pre-Expiry License Alert",
                "alert_type_uuid": "ABC",
                "auto_resolved": False,
                "check_id": "1234",
                "classifications": ["License"],
                "cluster_uuid": "1234",
                "context_types": [
                    "pre_expiry_msg",
                    "arithmos_id",
                    "ncc_version",
                    "nos_version",
                    "cluster_id",
                    "cluster_uuid",
                ],
                "context_values": [
                    "LIC-1234 - 1.00 NODE Pro expiring on 2025-01-31\nLIC-987654321 - 1.00 NODE Pro expiring on 2025-01-31",
                    "12234",
                    "123456789",
                    "1.2.3.4",
                    "9876",
                    "123-123-123",
                ],
                "created_time_stamp_in_usecs": 1731250394339858,
                "detailed_message": "",
                "id": "123-123-123",
                "impact_types": ["SystemIndicator"],
                "last_occurrence_time_stamp_in_usecs": 1731250394339858,
                "message": "Detailed license expiry info: {pre_expiry_msg}",
                "node_uuid": "14",
                "operation_type": "kCreate",
                "originating_cluster_uuid": "123-123-123-123",
                "possible_causes": [],
                "resolved": False,
                "resolved_by_username": "",
                "resolved_time_stamp_in_usecs": 0,
                "service_vmid": "123-123-123:444",
                "severity": "kInfo",
                "user_defined": False,
            }
        ],
        "metadata": {
            "count": 1000,
            "end_index": 7,
            "grand_total_entities": 7,
            "page": 1,
            "start_index": 1,
            "total_entities": 7,
        },
    }
    section = parse_prism_alerts([[json.dumps(data)]])
    assert section == [
        {
            "arithmos_id": "12234",
            "cluster_id": "9876",
            "cluster_uuid": "123-123-123",
            "message": "Detailed license expiry info: LIC-1234 - 1.00 NODE Pro "
            "expiring on 2025-01-31, LIC-987654321 - 1.00 NODE Pro expiring on "
            "2025-01-31",
            "ncc_version": "123456789",
            "nos_version": "1.2.3.4",
            "pre_expiry_msg": "LIC-1234 - 1.00 NODE Pro expiring on 2025-01-31\n"
            "LIC-987654321 - 1.00 NODE Pro expiring on 2025-01-31",
            "severity": "kInfo",
            "timestamp": 1731250394339858,
        }
    ]
    monkeypatch.setattr(time, "localtime", time.gmtime)
    assert list(
        check_prism_alerts(
            params={},
            section=section,
        )
    ) == [
        Result(state=State.OK, summary="1 alerts"),
        Result(
            state=State.OK,
            summary="Last worst on 2024-11-10 14:53:14: 'Detailed license expiry info: LIC-1234 - 1.00 NODE Pro expiring on 2025-01-31, LIC-987654321 - 1.00 NODE Pro expiring on 2025-01-31'",
        ),
        Result(state=State.OK, notice="\nLast 10 Alerts\n"),
        Result(
            state=State.OK,
            notice="2024-11-10 14:53:14\tDetailed license expiry info: LIC-1234 - 1.00 NODE Pro expiring on 2025-01-31, LIC-987654321 - 1.00 NODE Pro expiring on 2025-01-31",
        ),
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
                    summary="Last worst on 2022-10-06 14:16:27: 'It is recommended that NGT on the VM SRV-APP-01 with uuid 0000-0000 should be upgraded to the latest version supported by the cluster.NGT update contains bug fixes and improvements, which will improve the overall product experience.'",
                ),
                Result(state=State.OK, notice="\nLast 10 Alerts\n"),
                Result(
                    state=State.OK,
                    notice="2022-10-06 14:16:27\tIt is recommended that NGT on the VM SRV-APP-01 with uuid 0000-0000 should be upgraded to the latest version supported by the cluster.NGT update contains bug fixes and improvements, which will improve the overall product experience.",
                ),
                Result(
                    state=State.OK,
                    notice="2022-10-06 14:16:27\tIt is recommended that NGT on the VM SRV-SQL-02 with uuid 0000-0000 should be upgraded to the latest version supported by the cluster.NGT update contains bug fixes and improvements, which will improve the overall product experience.",
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
