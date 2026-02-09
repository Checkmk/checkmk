#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.rest_api_client import ClientRegistry


def test_list(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection, mock_wato_folders: None
) -> None:
    # just to make sure all filters can be returned
    live: MockLiveStatusConnection = mock_livestatus

    live.expect_query("GET hostgroups\nColumns: name alias")
    # for some reason this query doesn't run on the "NO_SITE" site, unless hostgroups have data
    live.expect_query("GET servicegroups\nColumns: name alias", sites=["local", "remote"])

    with live:
        resp = clients.VisualFilterClient.get_all()

    assert resp.status_code == 200
    assert resp.json["id"] == "all"


def test_list_filter_groups(clients: ClientRegistry) -> None:
    resp = clients.VisualFilterGroupClient.get_all()

    assert resp.status_code == 200
    assert len(resp.json["value"]) > 0
