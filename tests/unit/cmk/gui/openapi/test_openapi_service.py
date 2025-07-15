#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.ccc import version
from cmk.utils import paths
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

from tests.testlib.unit.rest_api_client import ClientRegistry

managedtest = pytest.mark.skipif(
    version.edition(paths.omd_root) is not version.Edition.CME, reason="see #7213"
)


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_openapi_livestatus_service_list(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    live.add_table(
        "services",
        [
            {
                "host_name": "heute",
                "host_alias": "heute",
                "description": "Filesystem /opt/omd/sites/heute/tmp",
                "state": 0,
                "state_type": "hard",
                "last_check": 1593697877,
                "acknowledged": 0,
            },
            {
                "host_name": "example.com",
                "host_alias": "example.com",
                "description": "Filesystem /boot",
                "state": 0,
                "state_type": "hard",
                "last_check": 0,
                "acknowledged": 0,
            },
        ],
    )

    live.expect_query(
        [
            "GET services",
            "Columns: host_name description",
        ],
    )

    with live:
        resp = clients.Service.get_all()
        assert len(resp.json["value"]) == 2

    live.expect_query(
        [
            "GET services",
            "Columns: host_name description",
            "Filter: host_alias ~ heute",
        ],
    )

    with live:
        resp = clients.Service.get_all(query={"op": "~", "left": "host_alias", "right": "heute"})

    assert len(resp.json["value"]) == 1


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_openapi_livestatus_service_list_for_host(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    live.add_table(
        "services",
        [
            {
                "host_name": "heute",
                "host_alias": "heute",
                "description": "Filesystem /opt/omd/sites/heute/tmp",
                "state": 0,
                "state_type": "hard",
                "last_check": 1593697877,
                "acknowledged": 0,
            },
            {
                "host_name": "example.com",
                "host_alias": "example.com",
                "description": "Filesystem /boot",
                "state": 0,
                "state_type": "hard",
                "last_check": 0,
                "acknowledged": 0,
            },
        ],
    )

    live.expect_query(
        [
            "GET services",
            "Columns: host_name description",
            "Filter: host_name = example.com",
        ]
    )
    with live:
        resp = clients.Host.get_all_services("example.com")

    assert len(resp.json["value"]) == 1


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_openapi_livestatus_collection_link(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    live.add_table(
        "services",
        [
            {
                "host_name": "heute",
                "host_alias": "heute",
                "description": "Filesystem /opt/omd/sites/heute/tmp",
                "state": 0,
                "state_type": "hard",
                "last_check": 1593697877,
                "acknowledged": 0,
            },
            {
                "host_name": "example.com",
                "host_alias": "example.com",
                "description": "Filesystem /boot",
                "state": 0,
                "state_type": "hard",
                "last_check": 0,
                "acknowledged": 0,
            },
        ],
    )

    live.expect_query(
        [
            "GET services",
            "Columns: host_name description",
        ],
    )

    with live:
        resp = clients.Service.get_all()

    assert (
        resp.json["value"][0]["links"][0]["href"]
        == "http://localhost/NO_SITE/check_mk/api/1.0/objects/host/heute/actions/show_service/invoke?service_description=Filesystem+%2Fopt%2Fomd%2Fsites%2Fheute%2Ftmp"
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_openapi_specific_service(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    live.add_table(
        "services",
        [
            {
                "host_name": "heute",
                "host_alias": "heute",
                "description": "Filesystem",
                "state": 0,
                "state_type": "hard",
                "last_check": 1593697877,
                "acknowledged": 0,
            },
            {
                "host_name": "example.com",
                "host_alias": "example.com",
                "description": "Filesystem /boot",
                "state": 0,
                "state_type": "hard",
                "last_check": 0,
                "acknowledged": 0,
            },
        ],
    )

    live.expect_query(
        [
            "GET services",
            "Columns: host_name description state state_type last_check",
            "Filter: host_name = heute",
            "Filter: description = Filesystem",
            "And: 2",
        ]
    )
    with live:
        resp = clients.Host.get_service("heute", "Filesystem")

    assert resp.json["extensions"] == {
        "description": "Filesystem",
        "host_name": "heute",
        "state_type": "hard",
        "state": 0,
        "last_check": 1593697877,
    }


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_openapi_specific_service_specific_columns(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    live.add_table(
        "services",
        [
            {
                "host_name": "heute",
                "host_alias": "heute",
                "description": "Filesystem",
                "state": 0,
                "state_type": "hard",
                "last_check": 1593697877,
                "acknowledged": 0,
            },
            {
                "host_name": "example.com",
                "host_alias": "example.com",
                "description": "Filesystem /boot",
                "state": 0,
                "state_type": "hard",
                "last_check": 0,
                "acknowledged": 0,
            },
        ],
    )

    live.expect_query(
        [
            "GET services",
            "Columns: state state_type",
            "Filter: host_name = heute",
            "Filter: description = Filesystem",
            "And: 2",
        ]
    )
    with live:
        resp = clients.Host.get_service("heute", "Filesystem", columns=["state", "state_type"])

    assert resp.json["extensions"] == {
        "state": 0,
        "state_type": "hard",
    }


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_openapi_service_with_slash_character(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    live.add_table(
        "services",
        [
            {
                "host_name": "heute",
                "host_alias": "heute",
                "description": "Filesystem",
                "state": 0,
                "state_type": "hard",
                "last_check": 1593697877,
                "acknowledged": 0,
            },
            {
                "host_name": "example.com",
                "host_alias": "example.com",
                "description": "Filesystem /böot",
                "state": 0,
                "state_type": "hard",
                "last_check": 0,
                "acknowledged": 0,
            },
        ],
    )

    live.expect_query(
        [
            "GET services",
            "Columns: host_name description state state_type last_check",
            "Filter: host_name = example.com",
            "Filter: description = Filesystem /böot",
            "And: 2",
        ]
    )
    with live:
        resp = clients.Host.get_service("example.com", "Filesystem /böot")

    assert resp.json["extensions"] == {
        "description": "Filesystem /böot",
        "host_name": "example.com",
        "state_type": "hard",
        "state": 0,
        "last_check": 0,
    }


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_openapi_non_existing_service(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    live.add_table(
        "services",
        [
            {
                "host_name": "heute",
                "host_alias": "heute",
                "description": "Filesystem",
                "state": 0,
                "state_type": "hard",
                "last_check": 1593697877,
                "acknowledged": 0,
            },
            {
                "host_name": "example.com",
                "host_alias": "example.com",
                "description": "Filesystem /boot",
                "state": 0,
                "state_type": "hard",
                "last_check": 0,
                "acknowledged": 0,
            },
        ],
    )

    live.expect_query(
        [
            "GET services",
            "Columns: host_name description state state_type last_check",
            "Filter: host_name = heute",
            "Filter: description = CPU",
            "And: 2",
        ]
    )

    with live:
        clients.Host.get_service("heute", "CPU", expect_ok=False).assert_status_code(404)


@managedtest
def test_openapi_get_host_services_with_guest_user(
    mock_livestatus: MockLiveStatusConnection,
    clients: ClientRegistry,
) -> None:
    mock_livestatus.add_table(
        "services",
        [
            {
                "host_name": "heute",
                "host_alias": "heute",
                "description": "Filesystem /opt/omd/sites/heute/tmp",
                "state": 0,
                "state_type": "hard",
                "last_check": 1593697877,
                "acknowledged": 0,
            },
        ],
    )

    clients.HostConfig.create(host_name="heute", folder="/")

    clients.User.create(
        username="guest_user1",
        fullname="guest_user1_alias",
        customer="provider",
        auth_option={"auth_type": "password", "password": "supersecretish"},
        roles=["guest"],
    )

    clients.HostConfig.set_credentials("guest_user1", "supersecretish")

    mock_livestatus.expect_query(
        [
            "GET services",
            "Columns: host_name description",
            "Filter: host_name = heute",
        ]
    )
    with mock_livestatus:
        resp = clients.Host.get_all_services("heute")

    assert len(resp.json["value"]) == 1
