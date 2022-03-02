#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This is mainly meant to test for rough data coming from livestatus and its errorhandling

In the near future some Datatypes will get sanitation, since this requires error handling, we
test for these conditions and its errorhandling. At the moment there are no errors but these
will raise as soon as we introduce sanitation and then these tests will fail.

CAUTION:
In the mock and in the livestatus module nearly all exceptions are "handled". Therfore you
don't see any here. So while debugging set some try/excepts and check for exceptions...
Example: If you request a Column not given in the data a KeyError is raised and
somewhere expected :-)
Also sometimes livestatus just tries again which can result in unexpected queries.
Good luck!
"""

import pytest

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from cmk.utils.type_defs import HostName

from cmk.gui.node_visualization import (
    ParentChildNetworkTopology,
    ParentChildTopologyPage,
    TopologySettings,
)


@pytest.fixture(name="rough_livestatus")
def rough_livestatus_mock(mock_livestatus: MockLiveStatusConnection) -> MockLiveStatusConnection:
    live = mock_livestatus
    live.set_sites(["foobar"])

    table = [
        {
            "name": "foo<(/",
            "host_name": "heute",
            "state": 0,
            "alias": "fooalias",
            "icon_image": "?",
            "parents": "?",
            "childs": "?",
            "has_been_checked": "?",
        },
        {
            "name": "bar<(/",
            "host_name": "heute",
            "state": 0,
            "alias": "fooalias",
            "icon_image": "?",
            "parents": "",
            "childs": "?",
            "has_been_checked": "?",
        },
    ]
    live.add_table("hosts", table)
    return live


def test_ParentChildNetworkTopology_fetch_data_for_hosts(
    rough_livestatus: MockLiveStatusConnection,
) -> None:
    settings = TopologySettings()
    topology = ParentChildNetworkTopology(topology_settings=settings)

    rough_livestatus.expect_query(
        "GET hosts\nColumns: name state alias icon_image parents childs has_been_checked\nFilter: host_name = heute\nOr: 1",
    )
    with rough_livestatus(expect_status_query=True):
        host_info = topology._fetch_data_for_hosts({HostName("heute")})
    assert host_info[0]["name"] == "foo<(/"


def test_ParentChildTopologyPage_get_hostnames_from_filters(
    rough_livestatus: MockLiveStatusConnection, mocker
) -> None:
    rough_livestatus.expect_query("GET hosts\nColumns: name\nColumnHeaders: off")

    class MockView:
        context = None

    mocker.patch(
        "cmk.gui.node_visualization.get_topology_view_and_filters",
        return_value=(MockView, []),
    )
    mocker.patch(
        "cmk.gui.plugins.visuals.utils.get_livestatus_filter_headers",
        return_value=[],
    )

    with rough_livestatus(expect_status_query=True):
        page = ParentChildTopologyPage()
        result_set = page._get_hostnames_from_filters({}, [])
    assert "foo<(/" in result_set


def test_ParentChildTopologyPage_get_default_view_hostnames(
    rough_livestatus: MockLiveStatusConnection,
) -> None:
    rough_livestatus.expect_query("GET hosts\nColumns: name\nFilter: parents =")
    with rough_livestatus(expect_status_query=True):
        page = ParentChildTopologyPage()
        result_set = page._get_default_view_hostnames(max_nodes=2)
    assert result_set.pop() == "bar<(/"
