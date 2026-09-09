#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.config import active_config
from tests.testlib.unit.rest_api_client import ClientRegistry


def test_show_graph_timerange_invalid_index(clients: ClientRegistry) -> None:
    error = (
        clients.GraphTimerange.get(graph_timerange_index=-1, expect_ok=False)
        .assert_status_code(404)
        .json
    )
    assert error["detail"] == "These fields have problems: path.index"
    assert error["fields"]["path.index"]["msg"] == "Input should be greater than or equal to 0"

    error = (
        clients.GraphTimerange.get(graph_timerange_index=999, expect_ok=False)
        .assert_status_code(404)
        .json
    )
    assert error["detail"] == "The graph timerange with the index 999 does not exists."


def test_list_graph_timeranges(clients: ClientRegistry) -> None:
    all_graph_timeranges = clients.GraphTimerange.get_all()
    assert len(all_graph_timeranges.json["value"]) == len(active_config.graph_timeranges)
    for graph_timerange in all_graph_timeranges.json["value"]:
        index = int(graph_timerange["id"])
        assert graph_timerange["domainType"] == "graph_timerange"
        assert len(graph_timerange["links"]) == 1
        assert graph_timerange["extensions"]["sort_index"] >= 0
        assert graph_timerange["extensions"]["sort_index"] == index
        assert (
            graph_timerange["extensions"]["total_seconds"]
            == active_config.graph_timeranges[index]["duration"]
        )
        assert graph_timerange["title"] == active_config.graph_timeranges[index]["title"]


def test_show_graph_timerange(clients: ClientRegistry) -> None:
    for index, graph_timerange in enumerate(active_config.graph_timeranges):
        apiGraphTimerange = clients.GraphTimerange.get(graph_timerange_index=index)
        assert apiGraphTimerange.json["domainType"] == "graph_timerange"
        assert apiGraphTimerange.json["id"] == str(index)
        assert apiGraphTimerange.json["title"] == graph_timerange["title"]
        assert apiGraphTimerange.json["extensions"]["sort_index"] == index
        assert apiGraphTimerange.json["extensions"]["total_seconds"] == graph_timerange["duration"]
