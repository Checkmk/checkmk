#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import patch

import pytest

from cmk.gui.availability.type_defs import AVEntry
from tests.testlib.rest_api_client import ClientRegistry
from tests.unit.cmk.gui.availability.openapi.conftest import TIME_FROM, TIME_UNTIL

_MODULE = "cmk.gui.availability.openapi.show_host_availability"


@pytest.mark.usefixtures("request_context")
def test_show_host_availability_returns_object(
    clients: ClientRegistry,
    host_av_entry: AVEntry,
) -> None:
    with (
        patch(f"{_MODULE}.get_availability_rawdata", return_value=({}, False)),
        patch(f"{_MODULE}.compute_availability", return_value=[host_av_entry]),
    ):
        resp = clients.HostAvailability.get(
            host_name="my-host",
            time_range_from=TIME_FROM,
            time_range_until=TIME_UNTIL,
        )

    assert resp.json["domainType"] == "host_availability"
    assert resp.json["id"] == "NO_SITE~my-host"
    assert resp.json["extensions"]["host"] == "my-host"
    assert resp.json["extensions"]["site"] == "NO_SITE"
    assert resp.json["extensions"]["states"]["up"] == 3600
    assert resp.json["extensions"]["states"]["down"] == 0


@pytest.mark.usefixtures("request_context")
def test_show_host_availability_returns_404_when_not_found(
    clients: ClientRegistry,
) -> None:
    with (
        patch(f"{_MODULE}.get_availability_rawdata", return_value=({}, False)),
        patch(f"{_MODULE}.compute_availability", return_value=[]),
    ):
        clients.HostAvailability.get(
            host_name="unknown-host",
            time_range_from=TIME_FROM,
            time_range_until=TIME_UNTIL,
            expect_ok=False,
        ).assert_status_code(404)
