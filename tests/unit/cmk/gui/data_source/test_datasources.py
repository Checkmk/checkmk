#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.data_source.datasources import DataSourceComments
from cmk.gui.data_source.registry import DataSourceRegistry, row_id


def test_comment_row_id_is_unique_per_site() -> None:
    # GIVEN
    registry = DataSourceRegistry()
    registry.register(DataSourceComments)
    datasource = DataSourceComments()

    row1 = {"site": "foo", "comment_id": "1"}
    row2 = {"site": "bar", "comment_id": "1"}

    # WHEN & THEN
    assert row_id(datasource.ident, row1) != row_id(datasource.ident, row2)
