#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import urllib

import pytest

from tests.testlib.unit.rest_api_client import ClientRegistry

from tests.unit.cmk.gui.conftest import CmkTestResponse, WebTestAppForCMK

from cmk.ccc import version

from cmk.utils import paths
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

managedtest = pytest.mark.skipif(
    version.edition(paths.omd_root) is not version.Edition.CME, reason="see #7213"
)


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_openapi_livestatus_service(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
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
        base = "/NO_SITE/check_mk/api/1.0"

        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            base + "/domain-types/service/collections/all",
            headers={"Accept": "application/json"},
            status=200,
        )
        assert len(resp.json["value"]) == 2

    live.expect_query(
        [
            "GET services",
            "Columns: host_name description",
            "Filter: host_alias ~ heute",
        ],
    )

    with live:
        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            base
            + '/domain-types/service/collections/all?query={"op": "~", "left": "host_alias", "right": "heute"}',
            headers={"Accept": "application/json"},
            status=200,
        )
        assert len(resp.json["value"]) == 1

    live.expect_query(
        [
            "GET services",
            "Columns: host_name description",
            "Filter: host_name = example.com",
        ]
    )
    with live:
        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            base + "/objects/host/example.com/collections/services",
            headers={"Accept": "application/json"},
            status=200,
        )
        assert len(resp.json["value"]) == 1


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_openapi_livestatus_collection_link(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
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
        base = "/NO_SITE/check_mk/api/1.0"

        resp: CmkTestResponse = aut_user_auth_wsgi_app.call_method(
            "get",
            base + "/domain-types/service/collections/all",
            headers={"Accept": "application/json"},
            params='{"include_links": True}',
            status=200,
        )

        assert (
            resp.json_body["value"][0]["links"][0]["href"]  # mypy: disable-error-code=index
            == "http://localhost/NO_SITE/check_mk/api/1.0/objects/host/heute/actions/show_service/invoke?service_description=Filesystem+%2Fopt%2Fomd%2Fsites%2Fheute%2Ftmp"
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_openapi_specific_service(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
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
        base = "/NO_SITE/check_mk/api/1.0"

        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            base + "/objects/host/heute/actions/show_service/invoke?service_description=Filesystem",
            headers={"Accept": "application/json"},
            status=200,
        )
        assert resp.json_body["extensions"] == {
            "description": "Filesystem",
            "host_name": "heute",
            "state_type": "hard",
            "state": 0,
            "last_check": 1593697877,
        }


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_openapi_specific_service_specific_columns(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
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
        base = "/NO_SITE/check_mk/api/1.0"

        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            base
            + "/objects/host/heute/actions/show_service/invoke?service_description=Filesystem&columns=state&columns=state_type",
            headers={"Accept": "application/json"},
            status=200,
        )
        assert resp.json_body["extensions"] == {
            "state": 0,
            "state_type": "hard",
        }


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_openapi_service_with_slash_character(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
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
        base = "/NO_SITE/check_mk/api/1.0"
        service_description = urllib.parse.quote("Filesystem /böot", safe=" ").replace(" ", "+")

        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            base
            + f"/objects/host/example.com/actions/show_service/invoke?service_description={service_description}",
            headers={"Accept": "application/json"},
            status=200,
        )
        assert resp.json_body["extensions"] == {
            "description": "Filesystem /böot",
            "host_name": "example.com",
            "state_type": "hard",
            "state": 0,
            "last_check": 0,
        }


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_openapi_non_existing_service(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
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
        base = "/NO_SITE/check_mk/api/1.0"

        _ = aut_user_auth_wsgi_app.call_method(
            "get",
            base + "/objects/host/heute/actions/show_service/invoke?service_description=CPU",
            headers={"Accept": "application/json"},
            status=404,
        )


@managedtest
def test_openapi_get_host_services_with_guest_user(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    clients: ClientRegistry,
    base: str,
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
        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            base + "/objects/host/heute/collections/services",
            headers={"Accept": "application/json"},
            status=200,
        )
        assert len(resp.json["value"]) == 1
