#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence
from http import HTTPStatus

import pytest

from cmk.ccc.user import UserId
from cmk.gui.monitor.hosts._api._custom_notification import (
    _handle_custom_notification,
    CustomNotificationHostRef,
    CustomNotificationRequestBody,
)
from cmk.gui.monitor.hosts._models import HostTarget
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK


class _FakeHostNotifier:
    def __init__(self) -> None:
        self.calls: list[tuple[list[HostTarget], dict[str, object]]] = []

    def send_custom_notification(
        self,
        targets: Sequence[HostTarget],
        *,
        author: UserId,
        comment: str,
        forced: bool,
        broadcast: bool,
    ) -> None:
        self.calls.append(
            (
                list(targets),
                {"author": author, "comment": comment, "forced": forced, "broadcast": broadcast},
            )
        )


def test_sends_one_notification_with_the_options_for_all_hosts() -> None:
    notifier = _FakeHostNotifier()
    body = CustomNotificationRequestBody(
        hosts=[
            CustomNotificationHostRef(site_id="local", name="web-01"),
            CustomNotificationHostRef(site_id="remote", name="web-02"),
        ],
        comment="Testing",
        forced=True,
        broadcast=False,
    )

    response = _handle_custom_notification(notifier, body, author=UserId("harry"))

    assert response.notified == 2
    assert notifier.calls == [
        (
            [HostTarget("local", "web-01"), HostTarget("remote", "web-02")],
            {"author": "harry", "comment": "Testing", "forced": True, "broadcast": False},
        )
    ]


def test_no_hosts_send_nothing() -> None:
    notifier = _FakeHostNotifier()

    response = _handle_custom_notification(
        notifier,
        CustomNotificationRequestBody(hosts=[], comment="Testing"),
        author=UserId("harry"),
    )

    assert response.notified == 0
    assert notifier.calls == []


@pytest.mark.usefixtures("with_admin_login")
def test_sends_the_command_to_the_site_of_the_host(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query(
        "COMMAND [...] SEND_CUSTOM_HOST_NOTIFICATION;heute;3;...;Testing", match_type="ellipsis"
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/hosts/actions/custom_notification",
            params=json.dumps(
                {
                    "hosts": [{"site_id": "NO_SITE", "name": "heute"}],
                    "comment": "Testing",
                    "forced": True,
                    "broadcast": True,
                }
            ),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"notified": 1}


@pytest.mark.usefixtures("with_admin_login")
def test_refuses_an_empty_comment(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    resp = aut_user_auth_wsgi_app.post(
        "/NO_SITE/check_mk/api/internal/monitor/hosts/actions/custom_notification",
        params=json.dumps({"hosts": [{"site_id": "NO_SITE", "name": "heute"}], "comment": ""}),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        status=HTTPStatus.BAD_REQUEST,
    )

    assert resp.status_code == HTTPStatus.BAD_REQUEST
