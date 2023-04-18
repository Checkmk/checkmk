#!/usr/bin/env python3
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
import json

import pytest

from tests.testlib.rest_api_client import ClientRegistry

from tests.unit.cmk.gui.conftest import SetConfig, WebTestAppForCMK

from cmk.utils import version
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

from cmk.gui.plugins.openapi.endpoints.downtime import _with_defaulted_timezone

managedtest = pytest.mark.skipif(not version.is_managed_edition(), reason="see #7213")


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_openapi_list_all_downtimes(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.expect_query(
        [
            "GET downtimes",
            "Columns: id host_name service_description is_service author start_time end_time recurring comment",
        ]
    )

    with live:
        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            base + "/domain-types/downtime/collections/all",
            headers={"Accept": "application/json"},
            status=200,
        )
        assert len(resp.json["value"]) == 1


@pytest.mark.usefixtures("with_groups")
def test_openapi_schedule_hostgroup_downtime(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "hostgroups",
        [
            {
                "members": ["example.com", "heute"],
                "name": "windows",
            },
        ],
    )
    live.expect_query("GET hostgroups\nColumns: members\nFilter: name = windows")
    live.expect_query(
        "GET hosts\nColumns: name\nFilter: name = example.com\nFilter: name = heute\nOr: 2"
    )
    live.expect_query("GET hosts\nColumns: name\nFilter: name = heute")
    live.expect_query(
        "COMMAND [...] SCHEDULE_HOST_DOWNTIME;heute;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    live.expect_query("GET hosts\nColumns: name\nFilter: name = example.com")
    live.expect_query(
        "COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/downtime/collections/host",
            content_type="application/json",
            params=json.dumps(
                {
                    "downtime_type": "hostgroup",
                    "hostgroup_name": "windows",
                    "start_time": "2020-01-01T00:00:00Z",
                    "end_time": "2020-01-02T00:00:00Z",
                }
            ),
            headers={"Accept": "application/json"},
            status=204,
        )


@pytest.mark.usefixtures("with_host")
def test_openapi_schedule_host_downtime(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.expect_query("GET hosts\nColumns: name\nFilter: name = example.com")
    live.expect_query("GET hosts\nColumns: name\nFilter: name = example.com")
    live.expect_query("GET hosts\nColumns: name\nFilter: name = example.com")
    live.expect_query(
        "COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/downtime/collections/host",
            content_type="application/json",
            params=json.dumps(
                {
                    "downtime_type": "host",
                    "host_name": "example.com",
                    "start_time": "2020-01-01T00:00:00Z",
                    "end_time": "2020-01-02T00:00:00Z",
                }
            ),
            headers={"Accept": "application/json"},
            status=204,
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_schedule_host_downtime_for_host_without_config(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    monitored_only_host = "this-host-only.exists-in.livestatus"

    live.add_table(
        "hosts",
        [
            {
                "name": monitored_only_host,
            },
        ],
    )

    live.expect_query("GET hosts\nColumns: name\nFilter: name = %s" % monitored_only_host)
    live.expect_query("GET hosts\nColumns: name\nFilter: name = %s" % monitored_only_host)
    live.expect_query("GET hosts\nColumns: name\nFilter: name = %s" % monitored_only_host)
    live.expect_query(
        "COMMAND [...] SCHEDULE_HOST_DOWNTIME;%s;1577836800;1577923200;1;0;0;test123-...;Downtime for ..."
        % monitored_only_host,
        match_type="ellipsis",
    )
    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/downtime/collections/host",
            content_type="application/json",
            params=json.dumps(
                {
                    "downtime_type": "host",
                    "host_name": monitored_only_host,
                    "start_time": "2020-01-01T00:00:00Z",
                    "end_time": "2020-01-02T00:00:00Z",
                }
            ),
            headers={"Accept": "application/json"},
            status=204,
        )


@pytest.mark.usefixtures("with_groups")
def test_openapi_schedule_servicegroup_downtime(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "servicegroups",
        [
            {
                "members": [
                    ["example.com", "Memory"],
                    ["example.com", "CPU load"],
                    ["heute", "CPU load"],
                ],
                "name": "routers",
            },
        ],
    )
    live.expect_query("GET servicegroups\nColumns: members\nFilter: name = routers")
    live.expect_query(
        "GET services\nColumns: description\nFilter: description = Memory\nFilter: host_name = example.com\nAnd: 2"
    )
    live.expect_query(
        "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    live.expect_query(
        "GET services\nColumns: description\nFilter: description = CPU load\nFilter: host_name = example.com\nAnd: 2"
    )
    live.expect_query(
        "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;CPU load;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    live.expect_query(
        "GET services\nColumns: description\nFilter: description = CPU load\nFilter: host_name = heute\nAnd: 2"
    )
    live.expect_query(
        "COMMAND [...] SCHEDULE_SVC_DOWNTIME;heute;CPU load;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/downtime/collections/service",
            content_type="application/json",
            params=json.dumps(
                {
                    "downtime_type": "servicegroup",
                    "servicegroup_name": "routers",
                    "start_time": "2020-01-01T00:00:00Z",
                    "end_time": "2020-01-02T00:00:00Z",
                }
            ),
            headers={"Accept": "application/json"},
            status=204,
        )


@pytest.mark.usefixtures("with_host")
def test_openapi_schedule_service_downtime(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.expect_query("GET hosts\nColumns: name\nFilter: name = example.com")
    live.expect_query(
        "GET services\nColumns: description\nFilter: description = Memory\nFilter: host_name = example.com\nAnd: 2"
    )
    live.expect_query(
        "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    live.expect_query(
        "GET services\nColumns: description\nFilter: description = CPU load\nFilter: host_name = example.com\nAnd: 2"
    )
    live.expect_query(
        "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;CPU load;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/downtime/collections/service",
            content_type="application/json",
            params=json.dumps(
                {
                    "downtime_type": "service",
                    "host_name": "example.com",
                    "service_descriptions": ["Memory", "CPU load"],
                    "start_time": "2020-01-01T00:00:00Z",
                    "end_time": "2020-01-02T00:00:00Z",
                }
            ),
            headers={"Accept": "application/json"},
            status=204,
        )


def test_openapi_schedule_service_downtime_with_non_matching_query(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.expect_query("GET services\nColumns: description host_name\nFilter: host_name = nothing")

    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/downtime/collections/service",
            content_type="application/json",
            params=json.dumps(
                {
                    "downtime_type": "service_by_query",
                    "query": {"op": "=", "left": "services.host_name", "right": "nothing"},
                    "start_time": "2020-01-01T00:00:00Z",
                    "end_time": "2020-01-02T00:00:00Z",
                }
            ),
            headers={"Accept": "application/json"},
            status=422,
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_schedule_host_downtime_with_non_matching_query(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.expect_query("GET hosts\nColumns: name\nFilter: name = nothing")

    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/downtime/collections/host",
            content_type="application/json",
            params=json.dumps(
                {
                    "downtime_type": "host_by_query",
                    "query": {"op": "=", "left": "hosts.name", "right": "nothing"},
                    "start_time": "2020-01-01T00:00:00Z",
                    "end_time": "2020-01-02T00:00:00Z",
                }
            ),
            headers={"Accept": "application/json"},
            status=422,
        )


def test_openapi_show_downtimes_with_query(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "downtimes",
        [
            {
                "id": 123,
                "host_name": "heute",
                "service_description": "CPU load",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "literally nothing",
            },
            {
                "id": 124,
                "host_name": "example.com",
                "service_description": "null",
                "is_service": 0,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some host downtime",
            },
        ],
    )

    live.expect_query(
        [
            "GET downtimes",
            "Columns: id host_name service_description is_service author start_time end_time recurring comment",
            "Filter: host_name ~ heute",
        ]
    )
    with live:
        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            base
            + '/domain-types/downtime/collections/all?query={"op": "~", "left": "downtimes.host_name", "right": "heute"}',
            headers={"Accept": "application/json"},
            status=200,
        )
    assert len(resp.json["value"]) == 1


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_show_downtime_with_params(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "downtimes",
        [
            {
                "id": 123,
                "host_name": "heute",
                "service_description": "CPU load",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "literally nothing",
            },
            {
                "id": 124,
                "host_name": "example.com",
                "service_description": "null",
                "is_service": 0,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some host downtime",
            },
        ],
    )

    live.expect_query(
        [
            "GET downtimes",
            "Columns: id host_name service_description is_service author start_time end_time recurring comment",
            "Filter: is_service = 0",
            "Filter: host_name = example.com",
            "And: 2",
        ]
    )
    with live:
        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            base
            + "/domain-types/downtime/collections/all?host_name=example.com&downtime_type=host",
            headers={"Accept": "application/json"},
            status=200,
        )
        assert resp.json_body["value"][0]["id"] == "124"


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_show_downtime_of_non_existing_host(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "downtimes",
        [
            {
                "id": 123,
                "host_name": "heute",
                "service_description": "CPU load",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "literally nothing",
            },
            {
                "id": 124,
                "host_name": "example.com",
                "service_description": "null",
                "is_service": 0,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some host downtime",
            },
        ],
    )

    live.expect_query(
        [
            "GET downtimes",
            "Columns: id host_name service_description is_service author start_time end_time recurring comment",
            "Filter: host_name = nothing",
        ]
    )
    with live:
        _ = aut_user_auth_wsgi_app.call_method(
            "get",
            base + "/domain-types/downtime/collections/all?host_name=nothing",
            headers={"Accept": "application/json"},
            status=200,
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_create_host_downtime_with_query(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "downtimes",
        [
            {
                "id": 123,
                "host_name": "heute",
                "service_description": "CPU load",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "literally nothing",
            },
            {
                "id": 124,
                "host_name": "example.com",
                "service_description": "null",
                "is_service": 0,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some host downtime",
            },
        ],
    )

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
            {
                "name": "example.com",
                "address": "0.0.0.0",
                "alias": "example",
                "downtimes_with_info": [],
                "scheduled_downtime_depth": 0,
            },
        ],
    )

    live.expect_query(["GET hosts", "Columns: name", "Filter: name ~ heute"])
    live.expect_query(["GET hosts", "Columns: name", "Filter: name = heute"])
    live.expect_query("GET hosts\nColumns: name\nFilter: name = heute")
    live.expect_query(
        "COMMAND [...] SCHEDULE_HOST_DOWNTIME;heute;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/downtime/collections/host",
            content_type="application/json",
            params=json.dumps(
                {
                    "downtime_type": "host_by_query",
                    "start_time": "2020-01-01T00:00:00Z",
                    "end_time": "2020-01-02T00:00:00Z",
                    "query": {"op": "~", "left": "hosts.name", "right": "heute"},
                }
            ),
            headers={"Accept": "application/json"},
            status=204,
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_create_service_downtime_with_query(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "services",
        [
            {
                "host_name": "heute",
                "host_alias": "heute",
                "description": "Memory",
                "state": 0,
                "state_type": "hard",
                "last_check": 1593697877,
                "acknowledged": 0,
            },
            {
                "host_name": "example",
                "host_alias": "example",
                "description": "CPU",
                "state": 0,
                "state_type": "hard",
                "last_check": 1593697877,
                "acknowledged": 0,
            },
        ],
    )

    live.expect_query(
        ["GET services", "Columns: description host_name", "Filter: host_name ~ heute"],
    )
    live.expect_query(
        "GET services\nColumns: description\nFilter: description = Memory\nFilter: host_name = heute\nAnd: 2"
    )
    live.expect_query(
        "COMMAND [...] SCHEDULE_SVC_DOWNTIME;heute;Memory;1577836800;1577923200;1;0;0;...;Downtime for service Memory@heute",
        match_type="ellipsis",
    )

    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/downtime/collections/service",
            content_type="application/json",
            params=json.dumps(
                {
                    "downtime_type": "service_by_query",
                    "start_time": "2020-01-01T00:00:00Z",
                    "end_time": "2020-01-02T00:00:00Z",
                    "query": {"op": "~", "left": "services.host_name", "right": "heute"},
                }
            ),
            headers={"Accept": "application/json"},
            status=204,
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_create_service_downtime_with_non_matching_query(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "services",
        [
            {
                "host_name": "heute",
                "host_alias": "heute",
                "description": "Memory",
                "state": 0,
                "state_type": "hard",
                "last_check": 1593697877,
                "acknowledged": 0,
            },
        ],
    )

    live.expect_query(
        ["GET services", "Columns: description host_name", "Filter: host_name ~ example"],
    )

    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/downtime/collections/service",
            content_type="application/json",
            params=json.dumps(
                {
                    "downtime_type": "service_by_query",
                    "start_time": "2020-01-01T00:00:00Z",
                    "end_time": "2020-01-02T00:00:00Z",
                    "query": {
                        "op": "~",
                        "left": "services.host_name",
                        "right": "example",
                    },
                }
            ),
            headers={"Accept": "application/json"},
            status=422,
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_delete_downtime_with_query(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "downtimes",
        [
            {
                "id": 123,
                "host_name": "heute",
                "service_description": "CPU load",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "literally nothing",
            },
            {
                "id": 124,
                "host_name": "example.com",
                "service_description": "null",
                "is_service": 0,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some host downtime",
            },
        ],
    )

    live.expect_query(
        ["GET downtimes", "Columns: id is_service", "Filter: host_name ~ heute"],
    )
    live.expect_query(
        "COMMAND [...] DEL_SVC_DOWNTIME;123",
        match_type="ellipsis",
    )

    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/downtime/actions/delete/invoke",
            content_type="application/json",
            params=json.dumps(
                {
                    "delete_type": "query",
                    "query": {"op": "~", "left": "downtimes.host_name", "right": "heute"},
                }
            ),
            headers={"Accept": "application/json"},
            status=204,
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_delete_downtime_by_id(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"
    live.add_table(
        "downtimes",
        [
            {
                "id": 123,
                "host_name": "heute",
                "service_description": "CPU load",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "literally nothing",
            },
            {
                "id": 1234,
                "host_name": "heute",
                "service_description": "Memory",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some service downtime",
            },
        ],
    )

    live.expect_query(
        [
            "GET downtimes",
            "Columns: is_service",
            "Filter: id = 123",
        ]
    )
    live.expect_query("COMMAND [...] DEL_SVC_DOWNTIME;123", match_type="ellipsis")

    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/downtime/actions/delete/invoke",
            content_type="application/json",
            params=json.dumps(
                {
                    "delete_type": "by_id",
                    "downtime_id": "123",
                }
            ),
            headers={"Accept": "application/json"},
            status=204,
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_delete_downtime_with_params(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "downtimes",
        [
            {
                "id": 123,
                "host_name": "heute",
                "service_description": "CPU load",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "literally nothing",
            },
            {
                "id": 124,
                "host_name": "heute",
                "service_description": "Memory",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some service downtime",
            },
        ],
    )

    live.expect_query(
        [
            "GET downtimes",
            "Columns: id is_service",
            "Filter: host_name = heute",
            "Filter: service_description = CPU load",
            "Filter: service_description = Memory",
            "Or: 2",
            "And: 2",
        ]
    )
    live.expect_query("COMMAND [...] DEL_SVC_DOWNTIME;123", match_type="ellipsis")
    live.expect_query("COMMAND [...] DEL_SVC_DOWNTIME;124", match_type="ellipsis")

    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/downtime/actions/delete/invoke",
            content_type="application/json",
            params=json.dumps(
                {
                    "delete_type": "params",
                    "host_name": "heute",
                    "service_descriptions": ["CPU load", "Memory"],
                }
            ),
            headers={"Accept": "application/json"},
            status=204,
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_delete_downtime_with_params_but_missing_downtime(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "downtimes",
        [],
    )

    live.expect_query(
        [
            "GET downtimes",
            "Columns: id is_service",
            "Filter: host_name = heute",
            "Filter: service_description = CPU load",
            "And: 2",
        ]
    )

    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/downtime/actions/delete/invoke",
            content_type="application/json",
            params=json.dumps(
                {
                    "delete_type": "params",
                    "host_name": "heute",
                    "service_descriptions": ["CPU load"],
                }
            ),
            headers={"Accept": "application/json"},
            status=204,
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_downtime_non_existing_instance(
    aut_user_auth_wsgi_app: WebTestAppForCMK, mock_livestatus: MockLiveStatusConnection
) -> None:
    base = "/NO_SITE/check_mk/api/1.0"
    live: MockLiveStatusConnection = mock_livestatus

    live.expect_query(["GET hosts", "Columns: name", "Filter: name = non-existant"])

    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/downtime/collections/host",
            content_type="application/json",
            params=json.dumps(
                {
                    "downtime_type": "host",
                    "host_name": "non-existant",
                    "start_time": "2020-01-01T00:00:00Z",
                    "end_time": "2020-01-02T00:00:00Z",
                }
            ),
            headers={"Accept": "application/json"},
            status=400,
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_downtime_non_existing_groups(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

    aut_user_auth_wsgi_app.post(
        base + "/domain-types/downtime/collections/host",
        content_type="application/json",
        params=json.dumps(
            {
                "downtime_type": "hostgroup",
                "hostgroup_name": "non-existant",
                "start_time": "2020-01-01T00:00:00Z",
                "end_time": "2020-01-02T00:00:00Z",
            }
        ),
        headers={"Accept": "application/json"},
        status=400,
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
@pytest.mark.parametrize("wato_enabled", [True, False])
def test_openapi_downtime_get_single(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    wato_enabled: bool,
    set_config: SetConfig,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "downtimes",
        [
            {
                "id": 123,
                "host_name": "heute",
                "service_description": "CPU load",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "literally nothing",
            },
            {
                "id": 124,
                "host_name": "heute",
                "service_description": "Memory",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some service downtime",
            },
        ],
    )

    live.expect_query(
        [
            "GET downtimes",
            "Columns: id host_name service_description is_service author start_time end_time recurring comment",
            "Filter: id = 123",
        ]
    )

    with live:
        with set_config(wato_enabled=wato_enabled):
            resp = aut_user_auth_wsgi_app.call_method(
                "get",
                base + "/objects/downtime/123",
                headers={"Accept": "application/json"},
                status=200,
            )
            assert resp.json_body["title"] == "Downtime for service: CPU load"


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_downtime_invalid_single(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.expect_query(
        [
            "GET downtimes",
            "Columns: id host_name service_description is_service author start_time end_time recurring comment",
            "Filter: id = 123",
        ]
    )

    with live:
        _ = aut_user_auth_wsgi_app.call_method(
            "get",
            base + "/objects/downtime/123",
            headers={"Accept": "application/json"},
            status=404,
        )


@managedtest
@pytest.mark.usefixtures("with_host")
@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_user_in_service_but_not_in_host_contact_group_regression(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    with_user: tuple[str, str],
) -> None:
    """Tests whether a user can put a service into downtime, even if she has no access to the host
    the service is run on.

    This test currently only checks that the right livestatus commands are send as mock_livestatus
    doesn't regard permissions as of now."""
    username, password = with_user

    clients.ContactGroup.bulk_create(
        groups=(
            {
                "name": "host_contact_group",
                "alias": "host_contact_group",
                "customer": "provider",
            },
            {
                "name": "service_contact_group",
                "alias": "service_contact_group",
                "customer": "provider",
            },
        )
    )

    clients.User.edit(username, contactgroups=["service_contact_group"])
    clients.Host.edit(
        host_name="heute", attributes={"contactgroups": {"groups": ["host_contact_group"]}}
    )

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
                "contact_groups": ["service_contact_group"],
            },
        ],
    )

    mock_livestatus.expect_query(
        f"GET hosts\nColumns: name\nFilter: name = heute\nAuthUser: {username}", match_type="loose"
    )

    mock_livestatus.expect_query(
        f"GET services\nColumns: description\nFilter: description = Filesystem /opt/omd/sites/heute/tmp\nFilter: host_name = heute\nAnd: 2\nAuthUser: {username}"
    )

    mock_livestatus.expect_query(
        f"COMMAND [...] SCHEDULE_SVC_DOWNTIME;heute;Filesystem /opt/omd/sites/heute/tmp;...;{username};Security updates",
        match_type="ellipsis",
    )

    with mock_livestatus():
        clients.Downtime.set_credentials(username, password)
        clients.Downtime.create_for_services(
            start_time=datetime.datetime.now(),
            end_time=datetime.datetime.now() + datetime.timedelta(minutes=5),
            recur="hour",
            duration=5 * 60,
            comment="Security updates",
            host_name="heute",
            service_descriptions=["Filesystem /opt/omd/sites/heute/tmp"],
        )


def test_with_defaulted_timezone() -> None:
    def _get_local_timezone():
        return datetime.timezone.utc

    assert _with_defaulted_timezone(
        datetime.datetime(year=1666, month=9, day=2), _get_local_timezone
    ) == datetime.datetime(1666, 9, 2, 0, 0, tzinfo=datetime.timezone.utc)
    assert _with_defaulted_timezone(
        datetime.datetime(year=1, month=1, day=1, tzinfo=datetime.timezone.min), _get_local_timezone
    ) == datetime.datetime(1, 1, 1, 0, 0, tzinfo=datetime.timezone.min)
