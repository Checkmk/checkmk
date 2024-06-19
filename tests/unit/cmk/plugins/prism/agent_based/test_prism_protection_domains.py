#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.prism.agent_based.prism_protection_domains import (
    check_prism_protection_domains,
    discovery_prism_protection_domains,
)

SECTION = {
    "NTX02-to-NTX01": {
        "active": False,
        "annotations": [],
        "cron_schedules": [],
        "hybrid_schedules_count": None,
        "marked_for_removal": False,
        "metro_avail": {
            "failure_handling": "Witness",
            "remote_site": "CLUNTX01",
            "role": "Standby",
            "status": "Disabled",
            "container": "CLUNTX02-PROD",
        },
        "min_snapshot_to_retain": None,
        "name": "NTX02-to-NTX01",
        "remote_site_names": [],
        "total_user_written_bytes": 121641153105,
        "usage_stats": {
            "dr.exclusive_snapshot_usage_bytes": "220155904",
            "hydration_space_bytes": "-1",
            "lws_store_used_bytes": "0",
        },
    },
}


@pytest.mark.parametrize(
    ["section", "expected_discovery_result"],
    [
        pytest.param(
            SECTION,
            [
                Service(item="NTX02-to-NTX01"),
            ],
            id="One service for every protection domain.",
        ),
        pytest.param({}, [], id="No services is discovered if no data exists."),
    ],
)
def test_discovery_prism_protection_domains(
    section: Mapping[str, Any],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discovery_prism_protection_domains(section)) == expected_discovery_result


@pytest.mark.parametrize(
    ["item", "params", "section", "expected_check_result"],
    [
        pytest.param(
            "NTX02-to-NTX01",
            {},
            SECTION,
            [
                Result(
                    state=State.CRIT,
                    summary="Type: Metro Availability, Role: Standby, Container: CLUNTX02-PROD, RemoteSite: CLUNTX01, Status: Disabled not Enabled(!)",
                ),
            ],
            id="If the protection domain is disabled and no rule exists the result is CRIT.",
        ),
        pytest.param(
            "NTX02-to-NTX01",
            {"sync_state": "Disabled"},
            SECTION,
            [
                Result(
                    state=State.OK,
                    summary="Type: Metro Availability, Role: Standby, Container: CLUNTX02-PROD, RemoteSite: CLUNTX01, Status: Disabled",
                ),
            ],
            id="If the protection domain is disabled and no rule exists the result is CRIT.",
        ),
    ],
)
def test_check_prism_protection_domains(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_protection_domains(
                item=item,
                params=params,
                section=section,
            )
        )
        == expected_check_result
    )
