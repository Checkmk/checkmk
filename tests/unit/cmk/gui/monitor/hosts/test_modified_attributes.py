#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import json
from collections.abc import Iterator, Sequence
from http import HTTPStatus

import pytest

from cmk.gui.config import Config
from cmk.gui.monitor.command import ModifiableAttribute
from cmk.gui.monitor.hosts._api._modified_attributes import (
    _handle_reset_modified_attributes,
    _handle_toggle_attribute,
    ModifiedAttributeHostRef,
    ResetModifiedAttributesRequestBody,
    ToggleAttributeRequestBody,
)
from cmk.gui.monitor.hosts._models import HostTarget
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.web_test_app import SetConfig, WebTestAppForCMK

_HOSTS = [
    ModifiedAttributeHostRef(site_id="local", name="web-01"),
    ModifiedAttributeHostRef(site_id="remote", name="web-02"),
]


@pytest.fixture(name="granted")
def fixture_granted(set_config: SetConfig, load_config: Config) -> Iterator[None]:
    # No role has these permissions by default, not even the admin.
    roles = copy.deepcopy(load_config.roles)
    roles["admin"]["permissions"] = {
        **roles["admin"].get("permissions", {}),
        "action.notifications": True,
        "action.enablechecks": True,
        "action.clearmodattr": True,
    }
    with set_config(roles=roles):
        yield


class _FakeHostAttributeModifier:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def toggle_attribute(
        self, targets: Sequence[HostTarget], attribute: ModifiableAttribute, *, enabled: bool
    ) -> None:
        self.calls.append(("toggle", list(targets), attribute, enabled))

    def reset_modified_attributes(self, targets: Sequence[HostTarget]) -> None:
        self.calls.append(("reset", list(targets)))


def test_toggles_the_attribute_of_all_hosts_at_once() -> None:
    modifier = _FakeHostAttributeModifier()
    body = ToggleAttributeRequestBody(
        hosts=_HOSTS, attribute=ModifiableAttribute.PASSIVE_CHECKS, enabled=False
    )

    response = _handle_toggle_attribute(modifier, body)

    assert response.modified == 2
    assert modifier.calls == [
        (
            "toggle",
            [HostTarget("local", "web-01"), HostTarget("remote", "web-02")],
            ModifiableAttribute.PASSIVE_CHECKS,
            False,
        )
    ]


def test_resets_the_modified_attributes_of_all_hosts_at_once() -> None:
    modifier = _FakeHostAttributeModifier()

    response = _handle_reset_modified_attributes(
        modifier, ResetModifiedAttributesRequestBody(hosts=_HOSTS)
    )

    assert response.modified == 2
    assert modifier.calls == [
        ("reset", [HostTarget("local", "web-01"), HostTarget("remote", "web-02")])
    ]


def test_no_hosts_send_nothing() -> None:
    modifier = _FakeHostAttributeModifier()

    _handle_toggle_attribute(
        modifier,
        ToggleAttributeRequestBody(
            hosts=[], attribute=ModifiableAttribute.NOTIFICATIONS, enabled=True
        ),
    )
    _handle_reset_modified_attributes(modifier, ResetModifiedAttributesRequestBody(hosts=[]))

    assert modifier.calls == []


@pytest.mark.parametrize(
    "attribute, enabled, command",
    [
        pytest.param("notifications", False, "DISABLE_HOST_NOTIFICATIONS", id="notifications off"),
        pytest.param("notifications", True, "ENABLE_HOST_NOTIFICATIONS", id="notifications on"),
        pytest.param("active_checks", False, "DISABLE_HOST_CHECK", id="active checks off"),
        pytest.param("passive_checks", True, "ENABLE_PASSIVE_HOST_CHECKS", id="passive checks on"),
    ],
)
@pytest.mark.usefixtures("with_admin_login", "granted")
def test_sends_the_toggle_to_the_site_of_the_host(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    attribute: str,
    enabled: bool,
    command: str,
) -> None:
    mock_livestatus.expect_query(f"COMMAND [...] {command};heute", match_type="ellipsis")

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/hosts/actions/toggle_attribute",
            params=json.dumps(
                {
                    "hosts": [{"site_id": "NO_SITE", "name": "heute"}],
                    "attribute": attribute,
                    "enabled": enabled,
                }
            ),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"modified": 1}


@pytest.mark.usefixtures("with_admin_login", "granted")
def test_sends_the_reset_to_the_site_of_the_host(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query("COMMAND [...] CHANGE_HOST_MODATTR;heute;0", match_type="ellipsis")

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/hosts/actions/reset_modified_attributes",
            params=json.dumps({"hosts": [{"site_id": "NO_SITE", "name": "heute"}]}),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"modified": 1}


@pytest.mark.usefixtures("with_admin_login", "granted")
def test_refuses_an_unknown_attribute(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    resp = aut_user_auth_wsgi_app.post(
        "/NO_SITE/check_mk/api/internal/monitor/hosts/actions/toggle_attribute",
        params=json.dumps(
            {
                "hosts": [{"site_id": "NO_SITE", "name": "heute"}],
                "attribute": "flap_detection",
                "enabled": False,
            }
        ),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        status=HTTPStatus.BAD_REQUEST,
    )

    assert resp.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.usefixtures("with_admin_login")
def test_toggling_notifications_needs_their_own_permission(
    aut_user_auth_wsgi_app: WebTestAppForCMK, set_config: SetConfig, load_config: Config
) -> None:
    roles = copy.deepcopy(load_config.roles)
    roles["admin"]["permissions"] = {
        **roles["admin"].get("permissions", {}),
        "action.enablechecks": True,
    }

    with set_config(roles=roles):
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/hosts/actions/toggle_attribute",
            params=json.dumps(
                {
                    "hosts": [{"site_id": "NO_SITE", "name": "heute"}],
                    "attribute": "notifications",
                    "enabled": False,
                }
            ),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            status=HTTPStatus.FORBIDDEN,
        )

    assert resp.status_code == HTTPStatus.FORBIDDEN
