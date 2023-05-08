#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import ast
import base64

import pytest

from tests.testlib.rest_api_client import ClientRegistry

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection


@pytest.fixture(autouse=True)
def everything_is_licensed(is_licensed: None) -> None:
    pass


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_livestatus_hosts_generic_filter(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "hosts",
        [
            {
                "name": "heute",
                "address": "127.0.0.1",
                "alias": "heute",
                "downtimes_with_info": [],
                "scheduled_downtime_depth": 0,
            },
        ],
    )

    live.expect_query(
        [
            "GET hosts",
            "Columns: name",
        ],
    )
    with live:
        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            base + "/domain-types/host/collections/all",
            headers={"Accept": "application/json"},
            status=200,
        )
        assert len(resp.json["value"]) == 1

    live.expect_query(
        [
            "GET hosts",
            "Columns: name alias",
            "Filter: alias ~ heute",
        ],
    )
    with live:
        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            base
            + '/domain-types/host/collections/all?query={"op": "~", "left": "alias", "right": "heute"}&columns=name&columns=alias',
            headers={"Accept": "application/json"},
            status=200,
        )
        assert len(resp.json["value"]) == 1


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_livestatus_hosts_empty_query(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:

    live = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"
    live.add_table(
        "hosts",
        [
            {
                "name": "heute",
                "address": "127.0.0.1",
                "alias": "heute",
                "downtimes_with_info": [],
                "scheduled_downtime_depth": 0,
            },
        ],
    )
    live.expect_query(
        [
            "GET hosts",
            "Columns: name alias",
        ],
    )
    with live:
        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            base + "/domain-types/host/collections/all?query={}&columns=name&columns=alias",
            headers={"Accept": "application/json"},
            status=200,
        )
        assert resp.json["value"][0]["id"] == "heute"


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_livestatus_hosts_single_column(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "hosts",
        [
            {
                "name": "heute",
                "address": "127.0.0.1",
                "alias": "heute",
                "downtimes_with_info": [],
                "scheduled_downtime_depth": 0,
            },
        ],
    )

    live.expect_query(
        [
            "GET hosts",
            "Columns: name",
            "Filter: alias ~ heute",
        ],
    )
    with live:
        aut_user_auth_wsgi_app.call_method(
            "get",
            base
            + '/domain-types/host/collections/all?query={"op": "~", "left": "alias", "right": "heute"}&columns=name',
            headers={"Accept": "application/json"},
            status=200,
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_livestatus_host_binary_data_as_base64(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binary_stuff = b"abcdefghijklmnopjrstuvwxyz\01\02\03\04\05"

    mock_livestatus.add_table(
        "hosts",
        [
            {
                "name": "heute",
                "address": "127.0.0.1",
                "alias": "heute",
                "downtimes_with_info": [],
                "scheduled_downtime_depth": 0,
                "mk_inventory_gz": binary_stuff,
            },
        ],
    )

    mock_livestatus.expect_query("GET hosts\nColumns: name mk_inventory_gz\nFilter: name = heute")

    with mock_livestatus():
        resp = clients.Host.get_all(
            query={"op": "=", "left": "name", "right": "heute"},
            columns=["mk_inventory_gz"],
        )

    assert resp.json["value"][0]["extensions"]["mk_inventory_gz"]["value_type"] == "binary_base64"

    assert resp.json["value"][0]["extensions"]["mk_inventory_gz"]["value"] == base64.encodebytes(
        binary_stuff
    ).decode("utf-8")


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_livestatus_host_inventory_not_json_serializable_regression(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    inventory_bytes = b"""{
        "Attributes": {},
        "Table": {},
        "Nodes": {
            "networking": {
                "Attributes": {
                    "Pairs": {
                        "hostname": "heute",
                        "available_ethernet_ports": 1337,
                        "total_ethernet_ports": 42,
                        "total_interfaces": 23,
                    }
                }
            }
        },
    }"""

    mock_livestatus.add_table(
        "hosts",
        [
            {
                "name": "heute",
                "address": "127.0.0.1",
                "alias": "heute",
                "downtimes_with_info": [],
                "scheduled_downtime_depth": 0,
                "mk_inventory": inventory_bytes,
            },
        ],
    )

    mock_livestatus.expect_query("GET hosts\nColumns: name mk_inventory\nFilter: name = heute")

    with mock_livestatus():
        resp = clients.Host.get_all(
            query={"op": "=", "left": "name", "right": "heute"},
            columns=["mk_inventory"],
        )

    assert resp.json["value"][0]["extensions"]["mk_inventory"] == ast.literal_eval(
        inventory_bytes.decode("utf-8")
    )
