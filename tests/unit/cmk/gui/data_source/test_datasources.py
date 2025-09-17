#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.data_source.datasources import DataSourceComments
from cmk.gui.data_source.registry import DataSourceRegistry, row_id
from tests.testlib.unit.rest_api_client import ClientRegistry


def test_comment_row_id_is_unique_per_site() -> None:
    # GIVEN
    registry = DataSourceRegistry()
    registry.register(DataSourceComments)
    datasource = DataSourceComments()

    row1 = {"site": "foo", "comment_id": "1"}
    row2 = {"site": "bar", "comment_id": "1"}

    # WHEN & THEN
    assert row_id(datasource.ident, row1) != row_id(datasource.ident, row2)


def test_list_data_sources(clients: ClientRegistry) -> None:
    resp = clients.ConstantClient.list_data_sources()
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.body!r}"
    assert len(resp.json["value"]) > 0, "Expected at least one data source to be returned"
