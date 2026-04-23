#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import patch

import pytest

from cmk.gui.availability.type_defs import AVEntry
from tests.testlib.rest_api_client import ClientRegistry
from tests.unit.cmk.gui.availability.openapi.conftest import TIME_FROM, TIME_UNTIL

_MODULE = "cmk.gui.availability.openapi.list_service_availability"


@pytest.mark.usefixtures("request_context")
def test_list_service_availability_returns_collection(
    clients: ClientRegistry,
    service_av_entry: AVEntry,
) -> None:
    with (
        patch(f"{_MODULE}.get_availability_rawdata", return_value=({}, False)),
        patch(f"{_MODULE}.compute_availability", return_value=[service_av_entry]),
    ):
        resp = clients.ServiceAvailability.list_all(
            site_id="NO_SITE",
            host_name="my-host",
            time_range_from=TIME_FROM,
            time_range_until=TIME_UNTIL,
        )

    assert resp.json["domainType"] == "service_availability"
    assert len(resp.json["value"]) == 1
    obj = resp.json["value"][0]
    assert obj["domainType"] == "service_availability"
    assert obj["extensions"]["host"] == "my-host"
    assert obj["extensions"]["service"] == "CPU load"
    assert obj["extensions"]["states"]["ok"] == 3600
    assert obj["extensions"]["states"]["crit"] == 0


@pytest.mark.usefixtures("request_context")
def test_list_service_availability_returns_empty_collection(
    clients: ClientRegistry,
) -> None:
    with (
        patch(f"{_MODULE}.get_availability_rawdata", return_value=({}, False)),
        patch(f"{_MODULE}.compute_availability", return_value=[]),
    ):
        resp = clients.ServiceAvailability.list_all(
            site_id="NO_SITE",
            host_name="my-host",
            time_range_from=TIME_FROM,
            time_range_until=TIME_UNTIL,
        )

    assert resp.json["value"] == []


@pytest.mark.usefixtures("request_context")
def test_list_service_availability_requires_site_id(
    clients: ClientRegistry,
) -> None:
    clients.ServiceAvailability.list_all(
        host_name="my-host",
        time_range_from=TIME_FROM,
        time_range_until=TIME_UNTIL,
        expect_ok=False,
    ).assert_status_code(400)


@pytest.mark.usefixtures("request_context")
def test_list_service_availability_requires_host_name(
    clients: ClientRegistry,
) -> None:
    clients.ServiceAvailability.list_all(
        site_id="NO_SITE",
        time_range_from=TIME_FROM,
        time_range_until=TIME_UNTIL,
        expect_ok=False,
    ).assert_status_code(400)
