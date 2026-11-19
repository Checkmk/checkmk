#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus
from unittest.mock import patch

import pytest

from cmk.gui.availability import AVData, AVEntry
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.rest_api_client import ClientRegistry, Response
from tests.unit.cmk.gui.availability.openapi.conftest import TIME_FROM, TIME_UNTIL

_MODULE = "cmk.gui.availability.openapi.list_service_availability"


def _list_all_with_patched_computation(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    *,
    site_id: str,
    computed: AVData,
) -> Response:
    with (
        patch(f"{_MODULE}.get_availability_rawdata", return_value=({}, False)),
        patch(f"{_MODULE}.compute_availability", return_value=computed),
        mock_livestatus,
    ):
        return clients.ServiceAvailability.list_all(
            site_id=site_id,
            host_name="my-host",
            time_range_from=TIME_FROM,
            time_range_until=TIME_UNTIL,
        )


@pytest.mark.usefixtures("request_context")
def test_list_service_availability_returns_collection(
    clients: ClientRegistry,
    service_av_entry: AVEntry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    resp = _list_all_with_patched_computation(
        clients, mock_livestatus, site_id="NO_SITE", computed=[service_av_entry]
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
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    resp = _list_all_with_patched_computation(
        clients, mock_livestatus, site_id="NO_SITE", computed=[]
    )

    assert resp.json["value"] == []


@pytest.mark.usefixtures("request_context")
def test_list_service_availability_names_a_site_that_does_not_answer(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.make_site_unreachable("remote")

    resp = _list_all_with_patched_computation(
        clients, mock_livestatus, site_id="remote", computed=[]
    )

    assert resp.json["extensions"] == {"unreachable_sites": ["remote"], "incomplete": True}


@pytest.mark.usefixtures("request_context")
def test_list_service_availability_requires_site_id(
    clients: ClientRegistry,
) -> None:
    clients.ServiceAvailability.list_all(
        host_name="my-host",
        time_range_from=TIME_FROM,
        time_range_until=TIME_UNTIL,
        expect_ok=False,
    ).assert_status_code(HTTPStatus.BAD_REQUEST)


@pytest.mark.usefixtures("request_context")
def test_list_service_availability_requires_host_name(
    clients: ClientRegistry,
) -> None:
    clients.ServiceAvailability.list_all(
        site_id="NO_SITE",
        time_range_from=TIME_FROM,
        time_range_until=TIME_UNTIL,
        expect_ok=False,
    ).assert_status_code(HTTPStatus.BAD_REQUEST)
