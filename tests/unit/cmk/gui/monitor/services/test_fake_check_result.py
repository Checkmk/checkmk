#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence
from http import HTTPStatus

import pytest

from cmk.ccc.user import UserId
from cmk.gui.monitor.services._api._fake_check_result import (
    _handle_fake_check_result,
    FakeCheckResultServiceRef,
    FakeCheckResultServicesRequestBody,
)
from cmk.gui.monitor.services._models import ServiceTarget
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK


class _FakeServiceCheckResultFaker:
    def __init__(self) -> None:
        self.calls: list[tuple[list[ServiceTarget], int, str]] = []

    def fake_check_result(
        self, targets: Sequence[ServiceTarget], *, state: int, output: str
    ) -> None:
        self.calls.append((list(targets), state, output))


def test_submits_the_state_with_the_default_output_for_every_service() -> None:
    faker = _FakeServiceCheckResultFaker()
    body = FakeCheckResultServicesRequestBody(
        services=[
            FakeCheckResultServiceRef(site_id="local", host_name="web-01", name="CPU load"),
            FakeCheckResultServiceRef(site_id="local", host_name="web-01", name="Memory"),
        ],
        state=2,
    )

    response = _handle_fake_check_result(faker, body, author=UserId("harry"))

    assert response.faked == 2
    assert faker.calls == [
        (
            [
                ServiceTarget("local", "web-01", "CPU load"),
                ServiceTarget("local", "web-01", "Memory"),
            ],
            2,
            "Manually set to Critical by harry",
        )
    ]


@pytest.mark.usefixtures("with_admin_login")
def test_sends_the_command_to_the_site_of_the_service(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query(
        "COMMAND [...] PROCESS_SERVICE_CHECK_RESULT;heute;CPU load;3;Testing",
        match_type="ellipsis",
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/services/actions/fake_check_result",
            params=json.dumps(
                {
                    "services": [{"site_id": "NO_SITE", "host_name": "heute", "name": "CPU load"}],
                    "state": 3,
                    "plugin_output": "Testing",
                }
            ),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"faked": 1}
