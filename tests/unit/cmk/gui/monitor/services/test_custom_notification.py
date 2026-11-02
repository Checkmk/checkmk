#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import json
from collections.abc import Sequence
from http import HTTPStatus

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.monitor.services._api._custom_notification import (
    _handle_custom_notification,
    CustomNotificationServiceRef,
    CustomNotificationServicesRequestBody,
)
from cmk.gui.monitor.services._models import ServiceTarget
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.web_test_app import SetConfig, WebTestAppForCMK


class _FakeServiceNotifier:
    def __init__(self) -> None:
        self.calls: list[tuple[list[ServiceTarget], dict[str, object]]] = []

    def send_custom_notification(
        self,
        targets: Sequence[ServiceTarget],
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


def test_sends_the_notification_for_every_service() -> None:
    notifier = _FakeServiceNotifier()
    body = CustomNotificationServicesRequestBody(
        services=[
            CustomNotificationServiceRef(site_id="local", host_name="web-01", name="CPU load"),
            CustomNotificationServiceRef(site_id="local", host_name="web-01", name="Memory"),
        ],
        comment="Testing",
        broadcast=True,
    )

    response = _handle_custom_notification(notifier, body, author=UserId("harry"))

    assert response.notified == 2
    assert notifier.calls == [
        (
            [
                ServiceTarget("local", "web-01", "CPU load"),
                ServiceTarget("local", "web-01", "Memory"),
            ],
            {"author": "harry", "comment": "Testing", "forced": False, "broadcast": True},
        )
    ]


@pytest.mark.usefixtures("with_admin_login")
def test_sends_the_command_to_the_site_of_the_service(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query(
        "COMMAND [...] SEND_CUSTOM_SVC_NOTIFICATION;heute;CPU load;0;...;Testing",
        match_type="ellipsis",
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/services/actions/custom_notification",
            params=json.dumps(
                {
                    "services": [{"site_id": "NO_SITE", "host_name": "heute", "name": "CPU load"}],
                    "comment": "Testing",
                }
            ),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"notified": 1}


@pytest.mark.usefixtures("with_admin_login")
def test_refuses_a_user_without_the_permission_to_send_custom_notifications(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    set_config: SetConfig,
    load_config: Config,
) -> None:
    roles = copy.deepcopy(load_config.roles)
    roles["admin"]["permissions"] = {
        **roles["admin"].get("permissions", {}),
        "action.customnotification": False,
    }

    with set_config(roles=roles), mock_livestatus(expect_status_query=False):
        aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/services/actions/custom_notification",
            params=json.dumps(
                {
                    "services": [{"site_id": "NO_SITE", "host_name": "heute", "name": "CPU load"}],
                    "comment": "Testing",
                }
            ),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            status=HTTPStatus.FORBIDDEN,
        )
