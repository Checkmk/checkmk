#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence
from http import HTTPStatus

import pytest

from cmk.ccc.user import UserId
from cmk.gui.monitor.hosts._api._fake_check_result import (
    _handle_fake_check_result,
    FakeCheckResultHostRef,
    FakeCheckResultRequestBody,
)
from cmk.gui.monitor.hosts._models import HostTarget
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK


class _FakeHostCheckResultFaker:
    def __init__(self) -> None:
        self.calls: list[tuple[list[HostTarget], int, str]] = []

    def fake_check_result(self, targets: Sequence[HostTarget], *, state: int, output: str) -> None:
        self.calls.append((list(targets), state, output))


def test_submits_the_state_with_the_default_output_for_all_hosts() -> None:
    faker = _FakeHostCheckResultFaker()
    body = FakeCheckResultRequestBody(
        hosts=[
            FakeCheckResultHostRef(site_id="local", name="web-01"),
            FakeCheckResultHostRef(site_id="remote", name="web-02"),
        ],
        state=1,
    )

    response = _handle_fake_check_result(faker, body, author=UserId("harry"))

    assert response.faked == 2
    assert faker.calls == [
        (
            [HostTarget("local", "web-01"), HostTarget("remote", "web-02")],
            1,
            "Manually set to Down by harry",
        )
    ]


def test_no_hosts_submit_nothing() -> None:
    faker = _FakeHostCheckResultFaker()

    response = _handle_fake_check_result(
        faker, FakeCheckResultRequestBody(hosts=[], state=0), author=UserId("harry")
    )

    assert response.faked == 0
    assert faker.calls == []


@pytest.mark.usefixtures("with_admin_login")
def test_sends_the_command_to_the_site_of_the_host(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query(
        "COMMAND [...] PROCESS_HOST_CHECK_RESULT;heute;1;Testing|rta=0.5ms", match_type="ellipsis"
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/hosts/actions/fake_check_result",
            params=json.dumps(
                {
                    "hosts": [{"site_id": "NO_SITE", "name": "heute"}],
                    "state": 1,
                    "plugin_output": "Testing",
                    "metrics": "rta=0.5ms",
                }
            ),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"faked": 1}


@pytest.mark.usefixtures("with_admin_login")
def test_refuses_a_service_state_for_a_host(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.post(
        "/NO_SITE/check_mk/api/internal/monitor/hosts/actions/fake_check_result",
        params=json.dumps({"hosts": [{"site_id": "NO_SITE", "name": "heute"}], "state": 2}),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        status=HTTPStatus.BAD_REQUEST,
    )
