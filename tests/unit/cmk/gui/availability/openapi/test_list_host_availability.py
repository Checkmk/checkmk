#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import patch

import pytest

from cmk.gui.availability.type_defs import AVEntry
from tests.testlib.rest_api_client import ClientRegistry
from tests.unit.cmk.gui.availability.openapi.conftest import TIME_FROM, TIME_UNTIL

_MODULE = "cmk.gui.availability.openapi.list_host_availability"


@pytest.mark.usefixtures("request_context")
def test_list_host_availability_returns_collection(
    clients: ClientRegistry,
    host_av_entry: AVEntry,
) -> None:
    with (
        patch(f"{_MODULE}.get_availability_rawdata", return_value=({}, False)),
        patch(f"{_MODULE}.compute_availability", return_value=[host_av_entry]),
    ):
        resp = clients.HostAvailability.list_all(
            time_range_from=TIME_FROM,
            time_range_until=TIME_UNTIL,
        )

    assert resp.json["domainType"] == "host_availability"
    assert len(resp.json["value"]) == 1
    obj = resp.json["value"][0]
    assert obj["domainType"] == "host_availability"
    assert obj["extensions"]["host"] == "my-host"
    assert obj["extensions"]["states"]["up"] == 3600
    assert obj["extensions"]["states"]["down"] == 0


@pytest.mark.usefixtures("request_context")
def test_list_host_availability_returns_empty_collection(
    clients: ClientRegistry,
) -> None:
    with (
        patch(f"{_MODULE}.get_availability_rawdata", return_value=({}, False)),
        patch(f"{_MODULE}.compute_availability", return_value=[]),
    ):
        resp = clients.HostAvailability.list_all(
            time_range_from=TIME_FROM,
            time_range_until=TIME_UNTIL,
        )

    assert resp.json["value"] == []


@pytest.mark.usefixtures("request_context")
def test_list_host_availability_rejects_inverted_time_range(
    clients: ClientRegistry,
) -> None:
    clients.HostAvailability.list_all(
        time_range_from=TIME_UNTIL,
        time_range_until=TIME_FROM,
        expect_ok=False,
    ).assert_status_code(400)
