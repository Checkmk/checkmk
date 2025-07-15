#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
import json

import pytest

from tests.testlib.unit.rest_api_client import ClientRegistry

from tests.unit.cmk.web_test_app import WebTestAppForCMK

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection


@pytest.mark.usefixtures("with_host")
@pytest.mark.parametrize(
    argnames=[
        "host_name",
        "service",
        "acknowledgement_sent",
    ],
    argvalues=[
        ["example.com", "CPU load", True],  # service Failed, acked.
        ["heute", "Memory", False],  # service OK, not failed.
    ],
)
def test_openapi_acknowledge_all_services(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    host_name: str,
    service: str,
    acknowledgement_sent: bool,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus
    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "services",
        [
            {"host_name": "example.com", "description": "CPU load", "state": 1},
            {"host_name": "heute", "description": "Memory", "state": 0},
        ],
    )

    live.expect_query([f"GET hosts\nColumns: name\nFilter: name = {host_name}"])
    live.expect_query(
        [
            "GET services",
            "Columns: host_name description state",
            f"Filter: host_name = {host_name}",
            f"Filter: description = {service}",
            "And: 2",
        ]
    )

    if acknowledgement_sent:
        live.expect_query([f"GET hosts\nColumns: name\nFilter: name = {host_name}"])
        live.expect_query(
            f"COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;{host_name};{service};2;1;1;test123-...;Hello world!",
            match_type="ellipsis",
        )

    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/acknowledge/collections/service",
            params=json.dumps(
                {
                    "acknowledge_type": "service",
                    "host_name": host_name,
                    "service_description": service,
                    "sticky": True,
                    "notify": True,
                    "persistent": True,
                    "comment": "Hello world!",
                }
            ),
            headers={"Accept": "application/json"},
            content_type="application/json",
            status=(204 if acknowledgement_sent else 422),
        )


@pytest.mark.parametrize(
    argnames=[
        "service",
        "acknowledgement_sent",
    ],
    argvalues=[
        ["Memory", True],  # ack sent
        ["Filesystem /boot", True],  # slashes in name, ack sent
        ["CPU load", False],  # service OK, ack not sent
    ],
)
def test_openapi_acknowledge_specific_service(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    service: str,
    acknowledgement_sent: bool,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus
    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "services",
        [
            {
                "host_name": "heute",
                "description": "Memory",
                "state": 1,
            },
            {
                "host_name": "heute",
                "description": "CPU load",
                "state": 0,
            },
            {
                "host_name": "heute",
                "description": "Filesystem /boot",
                "state": 1,
            },
        ],
    )

    live.expect_query(
        [
            "GET services",
            "Columns: host_name description state",
            "Filter: host_name ~ heute",
            f"Filter: description ~ {service}",
            "And: 2",
        ]
    )

    if acknowledgement_sent:
        live.expect_query("GET hosts\nColumns: name\nFilter: name = heute")
        live.expect_query(
            f"COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;heute;{service};2;1;1;test123-...;Hello world!",
            match_type="ellipsis",
        )

    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/acknowledge/collections/service",
            params=json.dumps(
                {
                    "acknowledge_type": "service_by_query",
                    "query": {
                        "op": "and",
                        "expr": [
                            {"op": "~", "left": "services.host_name", "right": "heute"},
                            {"op": "~", "left": "services.description", "right": service},
                        ],
                    },
                    "sticky": True,
                    "notify": True,
                    "persistent": True,
                    "comment": "Hello world!",
                }
            ),
            headers={"Accept": "application/json"},
            content_type="application/json",
            status=204,
        )


@pytest.mark.usefixtures("with_host")
@pytest.mark.parametrize(
    argnames=[
        "host_name",
        "acknowledgement_sent",
    ],
    argvalues=[
        ["example.com", True],  # host not ok, ack sent
        ["heute", False],  # host ok, ack not sent
    ],
)
def test_openapi_acknowledge_host(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    host_name: str,
    acknowledgement_sent: bool,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus
    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "hosts",
        [
            {
                "name": "example.com",
                "state": 1,
            },
            {
                "name": "heute",
                "state": 0,
            },
        ],
    )

    live.expect_query(f"GET hosts\nColumns: name\nFilter: name = {host_name}")
    live.expect_query(f"GET hosts\nColumns: state\nFilter: name = {host_name}")

    if acknowledgement_sent:
        live.expect_query(f"GET hosts\nColumns: name\nFilter: name = {host_name}")
        live.expect_query(
            f"COMMAND [...] ACKNOWLEDGE_HOST_PROBLEM;{host_name};2;1;1;test123-...;Hello world!",
            match_type="ellipsis",
        )

    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/acknowledge/collections/host",
            params=json.dumps(
                {
                    "acknowledge_type": "host",
                    "host_name": host_name,
                    "sticky": True,
                    "notify": True,
                    "persistent": True,
                    "comment": "Hello world!",
                }
            ),
            headers={"Accept": "application/json"},
            content_type="application/json",
            status=204 if acknowledgement_sent else 422,
        )


def test_openapi_bulk_acknowledge(
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
                "description": "Memory",
                "state": 1,
            },
            {"host_name": "example.com", "description": "CPU load", "state": 1},
        ],
    )

    live.expect_query(
        [
            "GET services",
            "Columns: host_name description state",
            "Filter: description = Memory",
            "Filter: description = CPU load",
            "Or: 2",
        ]
    )

    live.expect_query("GET hosts\nColumns: name\nFilter: name = heute")
    live.expect_query(
        "COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;heute;Memory;2;1;1;test123-...;Hello world!",
        match_type="ellipsis",
    )
    live.expect_query("GET hosts\nColumns: name\nFilter: name = example.com")
    live.expect_query(
        "COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;example.com;CPU load;2;1;1;test123-...;Hello world!",
        match_type="ellipsis",
    )

    with live():
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/acknowledge/collections/service",
            params=json.dumps(
                {
                    "acknowledge_type": "service_by_query",
                    "query": {
                        "op": "or",
                        "expr": [
                            {"op": "=", "left": "description", "right": "Memory"},
                            {"op": "=", "left": "description", "right": "CPU load"},
                        ],
                    },
                    "sticky": True,
                    "notify": True,
                    "persistent": True,
                    "comment": "Hello world!",
                }
            ),
            headers={"Accept": "application/json"},
            content_type="application/json",
            status=204,
        )


@pytest.mark.usefixtures("with_groups")
def test_openapi_acknowledge_servicegroup(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus
    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "servicegroups",
        [
            {
                "members": [("example.com", "Memory"), ("example.com", "CPU load")],
                "name": "routers",
            },
        ],
    )

    live.expect_query(
        "GET servicegroups\nColumns: name\nFilter: name = routers",
    )
    live.expect_query(
        "GET servicegroups\nColumns: members\nFilter: name = routers",
    )
    live.expect_query(
        "COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;example.com;Memory;1;0;0;test123-...;Acknowledged",
        match_type="ellipsis",
    )
    live.expect_query(
        "COMMAND [...] ACKNOWLEDGE_SVC_PROBLEM;example.com;CPU load;1;0;0;test123-...;Acknowledged",
        match_type="ellipsis",
    )
    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/acknowledge/collections/service",
            content_type="application/json",
            params=json.dumps(
                {
                    "acknowledge_type": "servicegroup",
                    "servicegroup_name": "routers",
                    "sticky": False,
                    "notify": False,
                    "persistent": False,
                    "comment": "Acknowledged",
                }
            ),
            headers={"Accept": "application/json"},
            status=204,
        )


@pytest.mark.usefixtures("with_groups")
def test_openapi_acknowledge_hostgroup(
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
    live.expect_query("GET hostgroups\nColumns: name\nFilter: name = windows")
    live.expect_query("GET hostgroups\nColumns: members\nFilter: name = windows")
    live.expect_query(
        "COMMAND [...] ACKNOWLEDGE_HOST_PROBLEM;example.com;1;0;0;test123-...;Acknowledged",
        match_type="ellipsis",
    )
    live.expect_query(
        "COMMAND [...] ACKNOWLEDGE_HOST_PROBLEM;heute;1;0;0;test123-...;Acknowledged",
        match_type="ellipsis",
    )

    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/acknowledge/collections/host",
            content_type="application/json",
            params=json.dumps(
                {
                    "acknowledge_type": "hostgroup",
                    "hostgroup_name": "windows",
                    "sticky": False,
                    "notify": False,
                    "persistent": False,
                    "comment": "Acknowledged",
                }
            ),
            headers={"Accept": "application/json"},
            status=204,
        )

    with live(expect_status_query=False):
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/acknowledge/collections/host",
            content_type="application/json",
            params=json.dumps(
                {
                    "acknowledge_type": "hostgroup",
                    "hostgroup_name": "twiddledee",
                    "sticky": False,
                    "notify": False,
                    "persistent": False,
                    "comment": "Acknowledged",
                }
            ),
            headers={"Accept": "application/json"},
            status=400,
        )

    # Test created but not monitored
    live.add_table("hostgroups", [])
    live.expect_query("GET hostgroups\nColumns: name\nFilter: name = windows")
    with live(expect_status_query=True):
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/acknowledge/collections/host",
            content_type="application/json",
            params=json.dumps(
                {
                    "acknowledge_type": "hostgroup",
                    "hostgroup_name": "windows",
                    "sticky": False,
                    "notify": False,
                    "persistent": False,
                    "comment": "Acknowledged",
                }
            ),
            headers={"Accept": "application/json"},
            status=400,
        )


def test_openapi_acknowledge_host_with_query(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus
    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "hosts",
        [
            {
                "name": "example.com",
                "state": 1,
            },
            {
                "name": "heute",
                "state": 0,
            },
        ],
    )

    live.expect_query("GET hosts\nColumns: name\nFilter: state = 1")
    live.expect_query("GET hosts\nColumns: name\nFilter: name = example.com")
    live.expect_query(
        "COMMAND [...] ACKNOWLEDGE_HOST_PROBLEM;example.com;1;0;0;test123...;Acknowledged",
        match_type="ellipsis",
    )

    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/acknowledge/collections/host",
            content_type="application/json",
            params=json.dumps(
                {
                    "acknowledge_type": "host_by_query",
                    "query": '{"op": "=", "left": "hosts.state", "right": "1"}',
                    "sticky": False,
                    "notify": False,
                    "persistent": False,
                    "comment": "Acknowledged",
                }
            ),
            headers={"Accept": "application/json"},
            status=204,
        )


def test_openapi_acknowledge_host_with_non_matching_query(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus
    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "hosts",
        [
            {
                "name": "example.com",
                "state": 1,
            },
            {
                "name": "heute",
                "state": 0,
            },
        ],
    )

    live.expect_query("GET hosts\nColumns: name\nFilter: name = servo")

    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/acknowledge/collections/host",
            content_type="application/json",
            params=json.dumps(
                {
                    "acknowledge_type": "host_by_query",
                    "query": '{"op": "=", "left": "hosts.name", "right": "servo"}',
                    "sticky": False,
                    "notify": False,
                    "persistent": False,
                    "comment": "Acknowledged",
                }
            ),
            headers={"Accept": "application/json"},
            status=422,
        )


@pytest.mark.usefixtures("with_host")
def test_openapi_acknowledge_host_with_expire_on(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus
    base = "/NO_SITE/check_mk/api/1.0"
    in_the_future = dt.datetime.now(dt.UTC) + dt.timedelta(days=1)

    live.add_table(
        "hosts",
        [
            {
                "name": "example.com",
                "state": 1,
            },
            {
                "name": "heute",
                "state": 0,
            },
        ],
    )

    live.expect_query(  # request data validation
        "GET hosts\nColumns: name\nFilter: name = example.com"
    )
    live.expect_query("GET hosts\nColumns: state\nFilter: name = example.com")
    live.expect_query("GET hosts\nColumns: name\nFilter: name = example.com")
    live.expect_query(
        f"COMMAND [...] ACKNOWLEDGE_HOST_PROBLEM;example.com;1;0;0;test123-...;Acknowledged;{int(in_the_future.timestamp())}",
        match_type="ellipsis",
    )
    with live:
        aut_user_auth_wsgi_app.post(
            base + "/domain-types/acknowledge/collections/host",
            content_type="application/json",
            params=json.dumps(
                {
                    "acknowledge_type": "host",
                    "host_name": "example.com",
                    "sticky": False,
                    "notify": False,
                    "persistent": False,
                    "comment": "Acknowledged",
                    "expire_on": in_the_future.isoformat(),
                }
            ),
            headers={"Accept": "application/json"},
            status=204,
        )


@pytest.mark.usefixtures("with_host")
@pytest.mark.parametrize(
    "host_name, expect_removal",
    [
        ["example.com", True],
        ["heute", False],
    ],
)
def test_openapi_remove_acknowledgement_for_host(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    host_name: str,
    expect_removal: bool,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    live.add_table(
        "hosts",
        [
            {"name": "example.com", "acknowledged": 1},
            {"name": "heute", "acknowledged": 0},
        ],
    )

    live.expect_query(  # request data validation
        f"GET hosts\nColumns: name\nFilter: name = {host_name}"
    )
    live.expect_query(
        [
            "GET hosts",
            "Columns: name",
            "Filter: acknowledged > 0",
            f"Filter: name = {host_name}",
            "And: 2",
        ]
    )
    if expect_removal:
        live.expect_query(
            f"COMMAND [...] REMOVE_HOST_ACKNOWLEDGEMENT;{host_name}",
            match_type="ellipsis",
        )

    with live:
        clients.Acknowledge.remove_for_host(host_name)


@pytest.mark.usefixtures("with_groups")
def test_openapi_remove_acknowledgement_for_host_group(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    live.add_table(
        "hosts",
        [
            {
                "name": "example.com",
                "acknowledged": 1,
                "groups": ["windows"],
            },
            {
                "name": "heute",
                "acknowledged": 0,
                "groups": ["windows"],
            },
            {
                "name": "Unrelated",
                "acknowledged": 1,
                "groups": [],
            },
        ],
    )
    live.add_table(
        "hostgroups",
        [{"name": "windows"}],
    )

    live.expect_query(  # request data validation
        [
            "GET hostgroups",
            "Columns: name",
            "Filter: name = windows",
        ]
    )
    live.expect_query(
        [
            "GET hosts",
            "Columns: name",
            "Filter: acknowledged > 0",
            "Filter: groups >= windows",
            "And: 2",
        ]
    )
    live.expect_query(
        "COMMAND [...] REMOVE_HOST_ACKNOWLEDGEMENT;example.com",
        match_type="ellipsis",
    )

    with live:
        clients.Acknowledge.remove_for_host_group("windows")


@pytest.mark.usefixtures("with_host")
@pytest.mark.parametrize(
    "host_name, service, expect_removal",
    [
        ["example.com", "CPU load", True],
        ["heute", "Memory", False],
    ],
)
def test_openapi_remove_acknowledgement_for_service(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    host_name: str,
    service: str,
    expect_removal: bool,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    live.add_table(
        "services",
        [
            {"host_name": "example.com", "description": "CPU load", "acknowledged": 1},
            {"host_name": "heute", "description": "Memory", "acknowledged": 0},
        ],
    )

    live.expect_query(  # request data validation
        f"GET hosts\nColumns: name\nFilter: name = {host_name}"
    )
    live.expect_query(
        [
            "GET services",
            "Columns: host_name description",
            "Filter: acknowledged > 0",
            f"Filter: host_name = {host_name}",
            f"Filter: description = {service}",
            "And: 3",
        ]
    )
    if expect_removal:
        live.expect_query(
            f"COMMAND [...] REMOVE_SVC_ACKNOWLEDGEMENT;{host_name};{service}",
            match_type="ellipsis",
        )

    with live:
        clients.Acknowledge.remove_for_service(host_name, service)


@pytest.mark.usefixtures("with_groups")
def test_openapi_remove_acknowledgement_for_service_group(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    live.add_table(
        "services",
        [
            {
                "host_name": "example.com",
                "description": "CPU load",
                "acknowledged": 1,
                "groups": ["routers"],
            },
            {
                "host_name": "heute",
                "description": "Memory",
                "acknowledged": 0,
                "groups": ["routers"],
            },
            {
                "host_name": "example.com",
                "description": "Unrelated",
                "acknowledged": 1,
                "groups": [],
            },
        ],
    )
    live.add_table(
        "servicegroups",
        [{"name": "routers"}],
    )

    live.expect_query(  # request data validation
        [
            "GET servicegroups",
            "Columns: name",
            "Filter: name = routers",
        ]
    )
    live.expect_query(
        [
            "GET services",
            "Columns: host_name description",
            "Filter: acknowledged > 0",
            "Filter: groups >= routers",
            "And: 2",
        ]
    )
    live.expect_query(
        "COMMAND [...] REMOVE_SVC_ACKNOWLEDGEMENT;example.com;CPU load",
        match_type="ellipsis",
    )

    with live:
        clients.Acknowledge.remove_for_service_group("routers")
