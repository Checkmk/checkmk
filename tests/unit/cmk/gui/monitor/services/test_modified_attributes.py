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
from cmk.gui.monitor.services._api._modified_attributes import (
    _handle_reset_modified_attributes,
    _handle_toggle_attribute,
    ModifiedAttributeServiceRef,
    ResetModifiedAttributesServicesRequestBody,
    ToggleAttributeServicesRequestBody,
)
from cmk.gui.monitor.services._models import ServiceTarget
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.web_test_app import SetConfig, WebTestAppForCMK

_SERVICES = [
    ModifiedAttributeServiceRef(site_id="local", host_name="web-01", name="CPU load"),
    ModifiedAttributeServiceRef(site_id="local", host_name="web-01", name="Memory"),
]
_TARGETS = [
    ServiceTarget("local", "web-01", "CPU load"),
    ServiceTarget("local", "web-01", "Memory"),
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


class _FakeServiceAttributeModifier:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def toggle_attribute(
        self, targets: Sequence[ServiceTarget], attribute: ModifiableAttribute, *, enabled: bool
    ) -> None:
        self.calls.append(("toggle", list(targets), attribute, enabled))

    def reset_modified_attributes(self, targets: Sequence[ServiceTarget]) -> None:
        self.calls.append(("reset", list(targets)))


def test_toggles_the_attribute_of_all_services_at_once() -> None:
    modifier = _FakeServiceAttributeModifier()
    body = ToggleAttributeServicesRequestBody(
        services=_SERVICES, attribute=ModifiableAttribute.ACTIVE_CHECKS, enabled=True
    )

    response = _handle_toggle_attribute(modifier, body)

    assert response.modified == 2
    assert modifier.calls == [("toggle", _TARGETS, ModifiableAttribute.ACTIVE_CHECKS, True)]


def test_resets_the_modified_attributes_of_all_services_at_once() -> None:
    modifier = _FakeServiceAttributeModifier()

    response = _handle_reset_modified_attributes(
        modifier, ResetModifiedAttributesServicesRequestBody(services=_SERVICES)
    )

    assert (response.modified, modifier.calls) == (2, [("reset", _TARGETS)])


@pytest.mark.parametrize(
    "attribute, enabled, command",
    [
        pytest.param("notifications", False, "DISABLE_SVC_NOTIFICATIONS", id="notifications off"),
        pytest.param("active_checks", True, "ENABLE_SVC_CHECK", id="active checks on"),
        pytest.param(
            "passive_checks", False, "DISABLE_PASSIVE_SVC_CHECKS", id="passive checks off"
        ),
    ],
)
@pytest.mark.usefixtures("with_admin_login", "granted")
def test_sends_the_toggle_to_the_site_of_the_service(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    attribute: str,
    enabled: bool,
    command: str,
) -> None:
    mock_livestatus.expect_query(f"COMMAND [...] {command};heute;CPU load", match_type="ellipsis")

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/services/actions/toggle_attribute",
            params=json.dumps(
                {
                    "services": [{"site_id": "NO_SITE", "host_name": "heute", "name": "CPU load"}],
                    "attribute": attribute,
                    "enabled": enabled,
                }
            ),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"modified": 1}


@pytest.mark.usefixtures("with_admin_login", "granted")
def test_sends_the_reset_to_the_site_of_the_service(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query(
        "COMMAND [...] CHANGE_SVC_MODATTR;heute;CPU load;0", match_type="ellipsis"
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/services/actions/reset_modified_attributes",
            params=json.dumps(
                {"services": [{"site_id": "NO_SITE", "host_name": "heute", "name": "CPU load"}]}
            ),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"modified": 1}
