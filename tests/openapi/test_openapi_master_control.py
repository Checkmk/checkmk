#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.ccc.user import UserId
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.rest_api_client import ClientRegistry

# A status row must carry the columns the GUI reads when connecting to a site (so the implicit
# connection query keeps working) plus the master control columns this endpoint family reads.
_CONNECTION_COLUMNS: Mapping[str, object] = {
    "livestatus_version": "2.5.0",
    "program_version": "Check_MK 2.5.0",
    "program_start": 1593770319,
    "max_long_output_size": 2000,
    "num_hosts": 1,
    "num_services": 36,
    "core_pid": 12345,
    "edition": "raw",
}

# The columns are queried in the order the toggles are defined in _utils.MASTER_CONTROL_TOGGLES.
_STATUS_COLUMNS = (
    "Columns: enable_notifications execute_service_checks execute_host_checks "
    "enable_flap_detection enable_event_handlers process_performance_data"
)


def _setup_status(
    mock_livestatus: MockLiveStatusConnection,
    *,
    notifications: int = 1,
    service_checks: int = 1,
    host_checks: int = 1,
    flap_detection: int = 1,
    event_handlers: int = 1,
    performance_data: int = 1,
) -> None:
    mock_livestatus.add_table(
        "status",
        [
            {
                **_CONNECTION_COLUMNS,
                "enable_notifications": notifications,
                "execute_service_checks": service_checks,
                "execute_host_checks": host_checks,
                "enable_flap_detection": flap_detection,
                "enable_event_handlers": event_handlers,
                "process_performance_data": performance_data,
            }
        ],
        "NO_SITE",
    )


def test_openapi_list_master_control(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _setup_status(
        mock_livestatus,
        notifications=1,
        service_checks=0,
        host_checks=1,
        flap_detection=0,
        event_handlers=1,
        performance_data=0,
    )
    mock_livestatus.expect_query(["GET status", _STATUS_COLUMNS])

    with mock_livestatus:
        resp = clients.MasterControl.get_all()

    assert len(resp.json["value"]) == 1
    entry = resp.json["value"][0]
    assert entry["domainType"] == "master_control"
    assert entry["id"] == "NO_SITE"
    assert entry["extensions"] == {
        "notifications": True,
        "service_checks": False,
        "host_checks": True,
        "flap_detection": False,
        "event_handlers": True,
        "performance_data": False,
    }


def test_openapi_show_master_control(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _setup_status(
        mock_livestatus,
        notifications=0,
        service_checks=1,
        host_checks=0,
        flap_detection=1,
        event_handlers=0,
        performance_data=1,
    )
    mock_livestatus.expect_query(["GET status", _STATUS_COLUMNS], sites=["NO_SITE"])

    with mock_livestatus:
        resp = clients.MasterControl.get("NO_SITE")

    assert resp.json["id"] == "NO_SITE"
    assert resp.json["extensions"] == {
        "notifications": False,
        "service_checks": True,
        "host_checks": False,
        "flap_detection": True,
        "event_handlers": False,
        "performance_data": True,
    }


def test_openapi_disable_notifications(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query("COMMAND [...] DISABLE_NOTIFICATIONS;", match_type="ellipsis")

    with mock_livestatus:
        resp = clients.MasterControl.edit("NO_SITE", {"notifications": False})

    assert resp.status_code == 204


def test_openapi_enable_notifications(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query("COMMAND [...] ENABLE_NOTIFICATIONS;", match_type="ellipsis")

    with mock_livestatus:
        resp = clients.MasterControl.edit("NO_SITE", {"notifications": True})

    assert resp.status_code == 204


def test_openapi_disable_service_checks(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query("COMMAND [...] STOP_EXECUTING_SVC_CHECKS;", match_type="ellipsis")

    with mock_livestatus:
        resp = clients.MasterControl.edit("NO_SITE", {"service_checks": False})

    assert resp.status_code == 204


def test_openapi_disable_host_checks(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query("COMMAND [...] STOP_EXECUTING_HOST_CHECKS;", match_type="ellipsis")

    with mock_livestatus:
        resp = clients.MasterControl.edit("NO_SITE", {"host_checks": False})

    assert resp.status_code == 204


def test_openapi_disable_flap_detection(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query("COMMAND [...] DISABLE_FLAP_DETECTION;", match_type="ellipsis")

    with mock_livestatus:
        resp = clients.MasterControl.edit("NO_SITE", {"flap_detection": False})

    assert resp.status_code == 204


def test_openapi_disable_event_handlers(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query("COMMAND [...] DISABLE_EVENT_HANDLERS;", match_type="ellipsis")

    with mock_livestatus:
        resp = clients.MasterControl.edit("NO_SITE", {"event_handlers": False})

    assert resp.status_code == 204


def test_openapi_disable_performance_data(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query("COMMAND [...] DISABLE_PERFORMANCE_DATA;", match_type="ellipsis")

    with mock_livestatus:
        resp = clients.MasterControl.edit("NO_SITE", {"performance_data": False})

    assert resp.status_code == 204


def test_openapi_update_empty_body_sends_no_command(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    # An empty body changes nothing, so the endpoint never touches Livestatus (no command and
    # not even the initial status query). The strict mock fails if any query is sent.
    with mock_livestatus(expect_status_query=False):
        resp = clients.MasterControl.edit("NO_SITE", {})

    assert resp.status_code == 204


def test_openapi_show_master_control_unknown_site(
    clients: ClientRegistry,
) -> None:
    resp = clients.MasterControl.get("not_a_site", expect_ok=False)
    assert resp.status_code == 404


def test_openapi_master_control_insufficient_permissions(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
) -> None:
    clients.MasterControl.set_credentials(*with_user)
    resp = clients.MasterControl.get_all(expect_ok=False)
    assert resp.status_code in (401, 403)
