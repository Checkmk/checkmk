#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime

import pytest

from cmk.ccc import version
from cmk.gui.openapi.endpoints.downtime import _with_defaulted_timezone
from cmk.utils import paths
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from tests.testlib.unit.rest_api_client import ClientRegistry
from tests.unit.cmk.web_test_app import SetConfig

managedtest = pytest.mark.skipif(
    version.edition(paths.omd_root) is not version.Edition.CME, reason="see #7213"
)


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_openapi_list_all_downtimes(
    mock_livestatus: MockLiveStatusConnection,
    clients: ClientRegistry,
) -> None:
    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id host_name service_description is_service author start_time end_time recurring comment",
        ]
    )

    with mock_livestatus:
        resp = clients.Downtime.get_all()
        assert len(resp.json["value"]) == 1
        assert resp.json["value"][0]["extensions"]["site_id"] == "NO_SITE"


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_openapi_list_all_downtimes_for_a_specific_site(
    mock_livestatus: MockLiveStatusConnection,
    clients: ClientRegistry,
) -> None:
    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id host_name service_description is_service author start_time end_time recurring comment",
        ],
        sites=["NO_SITE"],
    )

    with mock_livestatus:
        resp = clients.Downtime.get_all(site_id="NO_SITE")
        assert len(resp.json["value"]) == 1


@pytest.mark.usefixtures("with_groups")
def test_openapi_schedule_hostgroup_downtime(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
        "hostgroups",
        [
            {
                "members": ["example.com", "heute"],
                "name": "windows",
            },
        ],
        "NO_SITE",
    )
    mock_livestatus.expect_query("GET hostgroups\nColumns: members\nFilter: name = windows")
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_HOST_DOWNTIME;heute;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    with mock_livestatus:
        clients.Downtime.create_for_host(
            downtime_type="hostgroup",
            hostgroup_name="windows",
            start_time="2020-01-01T00:00:00Z",
            end_time="2020-01-02T00:00:00Z",
        )


@pytest.mark.usefixtures("with_host")
def test_openapi_schedule_host_downtime(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query("GET hosts\nColumns: name\nFilter: name = example.com")
    mock_livestatus.expect_query("GET hosts\nColumns: name\nFilter: name = example.com")
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_HOST_DOWNTIME;example.com;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    with mock_livestatus:
        clients.Downtime.create_for_host(
            downtime_type="host",
            host_name="example.com",
            start_time="2020-01-01T00:00:00Z",
            end_time="2020-01-02T00:00:00Z",
        )


@pytest.mark.usefixtures("with_host")
@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_schedule_host_downtime_for_host_without_config(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    host_name = "example.com"

    mock_livestatus.add_table(
        "hosts",
        [
            {
                "name": host_name,
            },
        ],
    )

    mock_livestatus.expect_query("GET hosts\nColumns: name\nFilter: name = %s" % host_name)
    mock_livestatus.expect_query("GET hosts\nColumns: name\nFilter: name = %s" % host_name)
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_HOST_DOWNTIME;%s;1577836800;1577923200;1;0;0;test123-...;Downtime for ..."
        % host_name,
        match_type="ellipsis",
    )
    with mock_livestatus:
        clients.Downtime.create_for_host(
            downtime_type="host",
            host_name=host_name,
            start_time="2020-01-01T00:00:00Z",
            end_time="2020-01-02T00:00:00Z",
        )


@pytest.mark.usefixtures("with_groups")
def test_openapi_schedule_servicegroup_downtime(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
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
    mock_livestatus.expect_query("GET servicegroups\nColumns: members\nFilter: name = routers")
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;CPU load;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_SVC_DOWNTIME;heute;CPU load;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    with mock_livestatus:
        clients.Downtime.create_for_services(
            downtime_type="servicegroup",
            servicegroup_name="routers",
            start_time="2020-01-01T00:00:00Z",
            end_time="2020-01-02T00:00:00Z",
        )


@pytest.mark.usefixtures("with_host")
def test_openapi_schedule_service_downtime(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query("GET hosts\nColumns: name\nFilter: name = example.com")
    mock_livestatus.expect_query(
        "GET services\nColumns: description\nFilter: host_name = example.com\nFilter: description = Memory\nFilter: description = CPU load\nOr: 2\nAnd: 2"
    )
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;Memory;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_SVC_DOWNTIME;example.com;CPU load;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    with mock_livestatus:
        clients.Downtime.create_for_services(
            downtime_type="service",
            host_name="example.com",
            service_descriptions=["Memory", "CPU load"],
            start_time="2020-01-01T00:00:00Z",
            end_time="2020-01-02T00:00:00Z",
        )


def test_openapi_schedule_service_downtime_with_non_matching_query(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query(
        "GET services\nColumns: description host_name\nFilter: host_name = nothing"
    )

    with mock_livestatus:
        clients.Downtime.create_for_services(
            downtime_type="service_by_query",
            query='{"op": "=", "left": "services.host_name", "right": "nothing"}',
            start_time="2020-01-01T00:00:00Z",
            end_time="2020-01-02T00:00:00Z",
            expect_ok=False,
        ).assert_status_code(422)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_schedule_host_downtime_with_non_matching_query(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query("GET hosts\nColumns: name\nFilter: name = nothing")

    with mock_livestatus:
        clients.Downtime.create_for_host(
            downtime_type="host_by_query",
            query='{"op": "=", "left": "hosts.name", "right": "nothing"}',
            start_time="2020-01-01T00:00:00Z",
            end_time="2020-01-02T00:00:00Z",
            expect_ok=False,
        ).assert_status_code(422)


def test_openapi_show_downtimes_with_query(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
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

    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id host_name service_description is_service author start_time end_time recurring comment",
            "Filter: host_name ~ heute",
        ]
    )
    with mock_livestatus:
        resp = clients.Downtime.get_all(
            query='{"op": "~", "left": "downtimes.host_name", "right": "heute"}'
        )
        assert len(resp.json["value"]) == 1


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_show_downtime_with_params(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
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

    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id host_name service_description is_service author start_time end_time recurring comment",
            "Filter: is_service = 0",
            "Filter: host_name = example.com",
            "And: 2",
        ]
    )
    with mock_livestatus:
        resp = clients.Downtime.get_all(host_name="example.com", downtime_type="host")
        assert resp.json["value"][0]["id"] == "124"


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_show_downtime_of_non_existing_host(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
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

    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id host_name service_description is_service author start_time end_time recurring comment",
            "Filter: host_name = nothing",
        ]
    )
    with mock_livestatus:
        clients.Downtime.get_all(host_name="nothing")


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_create_host_downtime_with_query(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
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

    mock_livestatus.add_table(
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

    mock_livestatus.expect_query(["GET hosts", "Columns: name", "Filter: name ~ heute"])
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_HOST_DOWNTIME;heute;1577836800;1577923200;1;0;0;test123-...;Downtime for ...",
        match_type="ellipsis",
    )
    with mock_livestatus:
        clients.Downtime.create_for_host(
            downtime_type="host_by_query",
            query='{"op": "~", "left": "hosts.name", "right": "heute"}',
            start_time="2020-01-01T00:00:00Z",
            end_time="2020-01-02T00:00:00Z",
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_create_service_downtime_with_query(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
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

    mock_livestatus.expect_query(
        ["GET services", "Columns: description host_name", "Filter: host_name ~ heute"],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] SCHEDULE_SVC_DOWNTIME;heute;Memory;1577836800;1577923200;1;0;0;...;Downtime for service Memory@heute",
        match_type="ellipsis",
    )

    with mock_livestatus:
        clients.Downtime.create_for_services(
            downtime_type="service_by_query",
            query='{"op": "~", "left": "services.host_name", "right": "heute"}',
            start_time="2020-01-01T00:00:00Z",
            end_time="2020-01-02T00:00:00Z",
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_create_service_downtime_with_non_matching_query(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
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

    mock_livestatus.expect_query(
        ["GET services", "Columns: description host_name", "Filter: host_name ~ example"],
    )

    with mock_livestatus:
        clients.Downtime.create_for_services(
            downtime_type="service_by_query",
            query='{"op": "~", "left": "services.host_name", "right": "example"}',
            start_time="2020-01-01T00:00:00Z",
            end_time="2020-01-02T00:00:00Z",
            expect_ok=False,
        ).assert_status_code(422)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_delete_downtime_with_query(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
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

    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id is_service",
            "Filter: host_name ~ heute",
        ],
    )
    mock_livestatus.expect_query(
        "COMMAND [...] DEL_SVC_DOWNTIME;123",
        match_type="ellipsis",
    )

    with mock_livestatus:
        clients.Downtime.delete(
            delete_type="query",
            query='{"op": "~", "left": "downtimes.host_name", "right": "heute"}',
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_delete_downtime_by_id(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
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

    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id is_service",
            "Filter: id = 123",
        ],
        sites=["NO_SITE"],
    )
    mock_livestatus.expect_query("COMMAND [...] DEL_SVC_DOWNTIME;123", match_type="ellipsis")

    with mock_livestatus:
        clients.Downtime.delete(
            site_id="NO_SITE",
            delete_type="by_id",
            downtime_id="123",
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_delete_downtime_with_params(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
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

    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id is_service",
            "Filter: host_name = heute",
            "Filter: service_description = CPU load",
            "Filter: service_description = Memory",
            "Or: 2",
            "And: 2",
        ],
    )
    mock_livestatus.expect_query("COMMAND [...] DEL_SVC_DOWNTIME;123", match_type="ellipsis")
    mock_livestatus.expect_query("COMMAND [...] DEL_SVC_DOWNTIME;124", match_type="ellipsis")

    with mock_livestatus:
        clients.Downtime.delete(
            delete_type="params",
            host_name="heute",
            service_descriptions=["CPU load", "Memory"],
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_delete_downtime_with_params_but_missing_downtime(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
        "downtimes",
        [],
    )

    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id is_service",
            "Filter: host_name = heute",
            "Filter: service_description = CPU load",
            "And: 2",
        ],
    )

    with mock_livestatus:
        clients.Downtime.delete(
            delete_type="params",
            host_name="heute",
            service_descriptions=["CPU load"],
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_delete_downtime_with_host_group(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    clients.HostGroup.create("windows", "windows")
    mock_livestatus.add_table(
        "hostgroups",
        [
            {
                "members": ["example.com", "foo.example.com"],
                "name": "windows",
            },
        ],
        "NO_SITE",
    )
    mock_livestatus.add_table(
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
                "comment": "some service downtime",
                "host_groups": [],
            },
            {
                "id": 124,
                "host_name": "example.com",
                "service_description": "Memory",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some service downtime",
                "host_groups": ["windows"],
            },
            {
                "id": 125,
                "host_name": "foo.example.com",
                "service_description": "Memory",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some service downtime",
                "host_groups": ["windows"],
            },
            {
                "id": 126,
                "host_name": "foo.example.com",
                "service_description": "null",
                "is_service": 0,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some host downtime",
                "host_groups": ["windows"],
            },
        ],
    )

    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id is_service",
            "Filter: host_groups ~~ windows",
        ],
    )
    mock_livestatus.expect_query("COMMAND [...] DEL_SVC_DOWNTIME;124", match_type="ellipsis")
    mock_livestatus.expect_query("COMMAND [...] DEL_SVC_DOWNTIME;125", match_type="ellipsis")
    mock_livestatus.expect_query("COMMAND [...] DEL_HOST_DOWNTIME;126", match_type="ellipsis")

    with mock_livestatus:
        clients.Downtime.delete(
            delete_type="hostgroup",
            host_group="windows",
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_delete_downtime_with_service_group(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    clients.ServiceGroup.create("CPU", "CPU")
    mock_livestatus.add_table(
        "servicegroups",
        [
            {
                "members": [
                    ["heute", "CPU load"],
                    ["example.com", "CPU load"],
                ],
                "name": "CPU",
            },
        ],
        "NO_SITE",
    )
    mock_livestatus.add_table(
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
                "comment": "some service downtime",
                "service_groups": ["CPU"],
            },
            {
                "id": 124,
                "host_name": "example.com",
                "service_description": "Memory",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some service downtime",
                "service_groups": ["CPU"],
            },
            {
                "id": 125,
                "host_name": "foo.example.com",
                "service_description": "Memory",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some service downtime",
                "service_groups": [],
            },
            {
                "id": 125,
                "host_name": "example.com",
                "service_description": "null",
                "is_service": 0,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some host downtime",
                "service_groups": [],
            },
        ],
    )

    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id is_service",
            "Filter: service_groups ~~ CPU",
        ],
    )
    mock_livestatus.expect_query("COMMAND [...] DEL_SVC_DOWNTIME;123", match_type="ellipsis")
    mock_livestatus.expect_query("COMMAND [...] DEL_SVC_DOWNTIME;124", match_type="ellipsis")

    with mock_livestatus:
        clients.Downtime.delete(
            delete_type="servicegroup",
            service_group="CPU",
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_delete_downtime_non_existing_host_group(
    clients: ClientRegistry,
) -> None:
    resp = clients.Downtime.delete(
        delete_type="hostgroup",
        host_group="non-existent",
        expect_ok=False,
    ).assert_status_code(400)
    assert resp.json["fields"]["hostgroup_name"] == ["Group missing: 'non-existent'"]


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_delete_downtime_non_existing_service_group(
    clients: ClientRegistry,
) -> None:
    resp = clients.Downtime.delete(
        delete_type="servicegroup",
        service_group="non-existent",
        expect_ok=False,
    ).assert_status_code(400)
    assert resp.json["fields"]["servicegroup_name"] == ["Group missing: 'non-existent'"]


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_downtime_non_existing_instance(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query("GET hosts\nColumns: name\nFilter: name = non-existent")

    with mock_livestatus:
        resp = clients.Downtime.create_for_host(
            downtime_type="host",
            host_name="non-existent",
            start_time="2020-01-01T00:00:00Z",
            end_time="2020-01-02T00:00:00Z",
            expect_ok=False,
        )
        resp.assert_status_code(400)

    assert resp.json["fields"]["host_name"] == [
        "Host 'non-existent' should be monitored but it's not. Activate the configuration?"
    ]


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_downtime_non_existing_groups(clients: ClientRegistry) -> None:
    clients.Downtime.create_for_host(
        downtime_type="hostgroup",
        hostgroup_name="non-existent",
        start_time="2020-01-01T00:00:00Z",
        end_time="2020-01-02T00:00:00Z",
        expect_ok=False,
    ).assert_status_code(400)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
@pytest.mark.parametrize("wato_enabled", [True, False])
def test_openapi_downtime_get_single(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    wato_enabled: bool,
    set_config: SetConfig,
) -> None:
    mock_livestatus.add_table(
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

    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id host_name service_description is_service author start_time end_time recurring comment",
            "Filter: id = 123",
        ],
        sites=["NO_SITE"],
    )

    with mock_livestatus:
        with set_config(wato_enabled=wato_enabled):
            resp = clients.Downtime.get(downtime_id=123, site_id="NO_SITE")
            assert resp.json["title"] == "Downtime for service: CPU load"


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_downtime_invalid_single(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id host_name service_description is_service author start_time end_time recurring comment",
            "Filter: id = 123",
        ],
        sites=["NO_SITE"],
    )

    with mock_livestatus:
        clients.Downtime.get(
            downtime_id=123,
            site_id="NO_SITE",
            expect_ok=False,
        ).assert_status_code(404)


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
    clients.HostConfig.edit(
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
        f"GET hosts\nColumns: name\nFilter: name = heute\nAuthUser: {username}"
    )
    mock_livestatus.expect_query(
        f"GET services\nColumns: description\nFilter: host_name = heute\nFilter: description = Filesystem /opt/omd/sites/heute/tmp\nAnd: 2\nAuthUser: {username}"
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
        return datetime.UTC

    assert _with_defaulted_timezone(
        datetime.datetime(year=1666, month=9, day=2), _get_local_timezone
    ) == datetime.datetime(1666, 9, 2, 0, 0, tzinfo=datetime.UTC)
    assert _with_defaulted_timezone(
        datetime.datetime(year=1, month=1, day=1, tzinfo=datetime.timezone.min), _get_local_timezone
    ) == datetime.datetime(1, 1, 1, 0, 0, tzinfo=datetime.timezone.min)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_service_description_for_service_downtimes(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
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

    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id host_name service_description is_service author start_time end_time recurring comment",
        ]
    )
    with mock_livestatus:
        resp = clients.Downtime.get_all()
        assert len(resp.json["value"]) == 2

        for val in resp.json["value"]:
            if val["extensions"]["is_service"]:
                assert val["extensions"]["service_description"] == "CPU load"
            else:
                assert "service_description" not in val["extensions"]


@pytest.mark.usefixtures("suppress_remote_automation_calls")
@pytest.mark.parametrize("service_downtime", [True, False])
def test_openapi_service_description_for_single_downtime(
    clients: ClientRegistry,
    service_downtime: bool,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
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
                "comment": "a service downtime",
            },
            {
                "id": 124,
                "host_name": "heute",
                "service_description": "null",
                "is_service": 0,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "a host downtime",
            },
        ],
    )

    service_id = 123 if service_downtime else 124

    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id host_name service_description is_service author start_time end_time recurring comment",
            f"Filter: id = {service_id}",
        ],
        sites=["NO_SITE"],
    )

    with mock_livestatus:
        resp = clients.Downtime.get(downtime_id=service_id, site_id="NO_SITE")

        assert resp.json["extensions"]["is_service"] == service_downtime

        if service_downtime:
            assert resp.json["extensions"]["service_description"] == "CPU load"
        else:
            assert "service_description" not in resp.json["extensions"]


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_modify_downtime_without_parameters(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    clients.Downtime.modify(
        modify_type="by_id",
        downtime_id="123",
        expect_ok=False,
    ).assert_status_code(400)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_modify_downtime_end_time(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
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
                "comment": "a service downtime",
            },
        ],
    )
    mock_livestatus.expect_query(
        "GET downtimes\nColumns: id is_service\nFilter: id = 123", sites=["NO_SITE"]
    )

    mock_livestatus.expect_query(
        "COMMAND [...] MODIFY_SVC_DOWNTIME;123;;1701913913;;;;...",
        match_type="ellipsis",
        sites=["NO_SITE"],
    )

    with mock_livestatus:
        clients.Downtime.modify(
            modify_type="by_id",
            site_id="NO_SITE",
            downtime_id="123",
            end_time="2023-12-07T01:51:53.000Z",
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
@pytest.mark.parametrize("end_time_delta", [10, -10])
def test_openapi_modify_downtime_delta_minutes(
    clients: ClientRegistry,
    end_time_delta: int,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    delta_seconds: str = "%s%d" % (
        "+" if end_time_delta > 0 else "-",
        abs(end_time_delta) * 60,
    )
    mock_livestatus.add_table(
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
                "comment": "a service downtime",
            },
        ],
    )
    mock_livestatus.expect_query(
        "GET downtimes\nColumns: id is_service\nFilter: id = 123", sites=["NO_SITE"]
    )

    mock_livestatus.expect_query(
        f"COMMAND [...] MODIFY_SVC_DOWNTIME;123;;{delta_seconds};...",
        match_type="ellipsis",
        sites=["NO_SITE"],
    )

    with mock_livestatus:
        clients.Downtime.modify(
            modify_type="by_id",
            site_id="NO_SITE",
            downtime_id="123",
            end_time=end_time_delta,
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_modify_downtime_comment(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
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
                "comment": "a service downtime",
            },
        ],
    )
    mock_livestatus.expect_query(
        "GET downtimes\nColumns: id is_service\nFilter: id = 123", sites=["NO_SITE"]
    )

    mock_livestatus.expect_query(
        "COMMAND [...] MODIFY_SVC_DOWNTIME;123;...;From API with love...",
        match_type="ellipsis",
        sites=["NO_SITE"],
    )

    with mock_livestatus:
        clients.Downtime.modify(
            modify_type="by_id", site_id="NO_SITE", downtime_id="123", comment="From API with love"
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_modify_downtime_with_host_group(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    clients.HostGroup.create("windows", "windows")
    mock_livestatus.add_table(
        "hostgroups",
        [
            {
                "members": ["example.com", "foo.example.com"],
                "name": "windows",
            },
        ],
        "NO_SITE",
    )
    mock_livestatus.add_table(
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
                "comment": "some service downtime",
                "host_groups": [],
            },
            {
                "id": 124,
                "host_name": "example.com",
                "service_description": "Memory",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some service downtime",
                "host_groups": ["windows"],
            },
            {
                "id": 125,
                "host_name": "foo.example.com",
                "service_description": "null",
                "is_service": 0,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some host downtime",
                "host_groups": ["windows"],
            },
        ],
    )

    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id is_service",
            "Filter: host_groups ~~ windows",
        ],
    )

    mock_livestatus.expect_query(
        "COMMAND [...] MODIFY_SVC_DOWNTIME;124;...;From API with love...",
        match_type="ellipsis",
        sites=["NO_SITE"],
    )

    mock_livestatus.expect_query(
        "COMMAND [...] MODIFY_HOST_DOWNTIME;125;...;From API with love...",
        match_type="ellipsis",
        sites=["NO_SITE"],
    )

    with mock_livestatus:
        clients.Downtime.modify(
            modify_type="hostgroup", host_group="windows", comment="From API with love"
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_modify_downtime_with_service_group(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    clients.ServiceGroup.create("CPU", "CPU")
    mock_livestatus.add_table(
        "servicegroups",
        [
            {
                "members": [
                    ["heute", "CPU load"],
                    ["example.com", "CPU load"],
                ],
                "name": "CPU",
            },
        ],
        "NO_SITE",
    )
    mock_livestatus.add_table(
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
                "comment": "some service downtime",
                "service_groups": ["CPU"],
            },
            {
                "id": 124,
                "host_name": "example.com",
                "service_description": "Memory",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some service downtime",
                "service_groups": ["CPU"],
            },
            {
                "id": 125,
                "host_name": "foo.example.com",
                "service_description": "Memory",
                "is_service": 1,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some service downtime",
                "service_groups": [],
            },
            {
                "id": 125,
                "host_name": "example.com",
                "service_description": "null",
                "is_service": 0,
                "author": "random",
                "start_time": 1606913913,
                "end_time": 1606913913,
                "recurring": 0,
                "comment": "some host downtime",
                "service_groups": [],
            },
        ],
    )

    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id is_service",
            "Filter: service_groups ~~ CPU",
        ],
    )

    mock_livestatus.expect_query(
        "COMMAND [...] MODIFY_SVC_DOWNTIME;123;...;From API with love...",
        match_type="ellipsis",
        sites=["NO_SITE"],
    )

    mock_livestatus.expect_query(
        "COMMAND [...] MODIFY_SVC_DOWNTIME;124;...;From API with love...",
        match_type="ellipsis",
        sites=["NO_SITE"],
    )

    with mock_livestatus:
        clients.Downtime.modify(
            modify_type="servicegroup", service_group="CPU", comment="From API with love"
        )


# TODO: Delta must be different than zero
def test_openapi_modify_downtime_delta_minutes_cannot_be_zero(
    clients: ClientRegistry,
) -> None:
    clients.Downtime.modify(
        modify_type="by_id",
        site_id="NO_SITE",
        downtime_id="123",
        end_time=0,
        expect_ok=False,
    ).assert_status_code(400)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_modify_downtime_non_existing_host_group(
    clients: ClientRegistry,
) -> None:
    resp = clients.Downtime.modify(
        modify_type="hostgroup",
        host_group="non-existent",
        expect_ok=False,
    ).assert_status_code(400)
    assert resp.json["fields"]["hostgroup_name"] == ["Group missing: 'non-existent'"]


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_modify_downtime_non_existing_service_group(
    clients: ClientRegistry,
) -> None:
    resp = clients.Downtime.modify(
        modify_type="servicegroup",
        service_group="non-existent",
        expect_ok=False,
    ).assert_status_code(400)
    assert resp.json["fields"]["servicegroup_name"] == ["Group missing: 'non-existent'"]


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_downtime_fields_format(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
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

    mock_livestatus.expect_query(
        [
            "GET downtimes",
            "Columns: id host_name service_description is_service author start_time end_time recurring comment",
            "Filter: is_service = 0",
            "Filter: host_name = example.com",
            "And: 2",
        ]
    )
    with mock_livestatus:
        resp = clients.Downtime.get_all(host_name="example.com", downtime_type="host")
        for dt in resp.json["value"]:
            attributes = dt["extensions"]
            assert isinstance(attributes["recurring"], bool)
            assert isinstance(attributes["is_service"], bool)
