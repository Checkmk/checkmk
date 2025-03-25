#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.structured_data import deserialize_tree, ImmutableTree, SDNodeName

from cmk.gui.painter.v0 import JoinCell, painter_registry
from cmk.gui.type_defs import ColumnSpec, PainterParameters
from cmk.gui.views.inventory._row_post_processor import _join_inventory_rows


@pytest.mark.usefixtures("request_context")
def test_row_post_processor() -> None:
    class _FakeJoinCell(JoinCell):
        def painter_parameters(self) -> PainterParameters | None:
            return self._painter_params

    rows = [
        {
            "site": "mysite",
            "host_name": "my-host-name1",
            "invorainstance_sid": "sid1",
            "invorainstance_version": "version1",
            "invorainstance_bar": "bar",
            "host_inventory": deserialize_tree(
                {
                    "Attributes": {},
                    "Nodes": {
                        "path-to": {
                            "Attributes": {},
                            "Nodes": {
                                "ora-dataguard-stats": {
                                    "Attributes": {},
                                    "Nodes": {},
                                    "Table": {
                                        "KeyColumns": ["sid"],
                                        "Rows": [
                                            {
                                                "sid": "sid1",
                                                "db_unique": "name1",
                                                "role": "role1",
                                                "switchover": "switchover1",
                                            },
                                            {
                                                "sid": "sid2",
                                                "db_unique": "name2",
                                                "role": "role2",
                                                "switchover": "switchover2",
                                            },
                                        ],
                                    },
                                },
                                "ora-versions": {
                                    "Attributes": {},
                                    "Nodes": {},
                                    "Table": {
                                        "KeyColumns": ["version"],
                                        "Rows": [
                                            {
                                                "version": "version1",
                                                "edition": "edition1",
                                            },
                                            {
                                                "version": "version2",
                                                "edition": "edition2",
                                            },
                                        ],
                                    },
                                },
                                "ora-foobar": {
                                    "Attributes": {},
                                    "Nodes": {},
                                    "Table": {
                                        "KeyColumns": ["foo"],
                                        "Rows": [
                                            {
                                                "foo": "foo1",
                                                "bar": "bar",
                                            },
                                            {
                                                "foo": "foo2",
                                                "bar": "bar",
                                            },
                                        ],
                                    },
                                },
                            },
                            "Table": {},
                        },
                    },
                    "Table": {},
                }
            ),
        },
        {
            "site": "mysite2",
            "host_name": "my-host-name2",
            "invorainstance_sid": "sid1",
            "invorainstance_version": "version1",
            "invorainstance_bar": "bar",
            "host_inventory": ImmutableTree(),
        },
    ]

    expected_len = len(rows)

    _join_inventory_rows(
        view_macros=[
            ("sid", "$SID$"),
            ("version", "$VERSION$"),
            ("bar", "$BAR$"),
        ],
        view_join_cells=[
            # Matches 'sid'
            _FakeJoinCell(
                ColumnSpec(
                    name="invoradataguardstats_db_unique",
                    parameters=PainterParameters(
                        path_to_table=(SDNodeName("path-to"), SDNodeName("ora-dataguard-stats")),
                        column_to_display="db_unique",
                        columns_to_match=[("sid", "$SID$")],
                    ),
                    join_value="invoradataguardstats_db_unique",
                    _column_type="join_inv_column",
                ),
                "",
                painter_registry,
            ),
            # Match 'version'
            _FakeJoinCell(
                ColumnSpec(
                    name="invoraversions_edition",
                    parameters=PainterParameters(
                        path_to_table=(SDNodeName("path-to"), SDNodeName("ora-versions")),
                        column_to_display="edition",
                        columns_to_match=[("version", "$VERSION$")],
                    ),
                    join_value="invoraversions_edition",
                    _column_type="join_inv_column",
                ),
                "",
                painter_registry,
            ),
            # Match 'bar', not unique
            _FakeJoinCell(
                ColumnSpec(
                    name="invorafoobar_foo",
                    parameters=PainterParameters(
                        path_to_table=(SDNodeName("path-to"), SDNodeName("ora-foobar")),
                        column_to_display="foo",
                        columns_to_match=[("bar", "$BAR$")],
                    ),
                    join_value="invorafoobar_foo",
                    _column_type="join_inv_column",
                ),
                "",
                painter_registry,
            ),
            # Unknown macro
            _FakeJoinCell(
                ColumnSpec(
                    name="invoradataguardstats_role",
                    parameters=PainterParameters(
                        path_to_table=(SDNodeName("path-to"), SDNodeName("ora-dataguard-stats")),
                        column_to_display="role",
                        columns_to_match=[("sid", "$BAZ$")],
                    ),
                    join_value="invoradataguardstats_role",
                    _column_type="join_inv_column",
                ),
                "",
                painter_registry,
            ),
            # Unknown node
            _FakeJoinCell(
                ColumnSpec(
                    name="invunknown_column_name",
                    parameters=PainterParameters(
                        path_to_table=(SDNodeName("path-to"), SDNodeName("somewhere-else")),
                        column_to_display="column_name",
                        columns_to_match=[("sid", "$SID$")],
                    ),
                    join_value="invunknown_column_name",
                    _column_type="join_inv_column",
                ),
                "",
                painter_registry,
            ),
        ],
        view_datasource_ident="invorainstance",
        rows=rows,
    )

    assert len(rows) == expected_len

    for row, expected_row in zip(
        rows,
        [
            {
                "site": "mysite",
                "host_name": "my-host-name1",
                "invorainstance_sid": "sid1",
                "invorainstance_version": "version1",
                "invorainstance_bar": "bar",
                "host_inventory": deserialize_tree(
                    {
                        "Attributes": {},
                        "Nodes": {
                            "path-to": {
                                "Attributes": {},
                                "Nodes": {
                                    "ora-dataguard-stats": {
                                        "Attributes": {},
                                        "Nodes": {},
                                        "Table": {
                                            "KeyColumns": ["sid"],
                                            "Rows": [
                                                {
                                                    "sid": "sid1",
                                                    "db_unique": "name1",
                                                    "role": "role1",
                                                    "switchover": "switchover1",
                                                },
                                                {
                                                    "sid": "sid2",
                                                    "db_unique": "name2",
                                                    "role": "role2",
                                                    "switchover": "switchover2",
                                                },
                                            ],
                                        },
                                    },
                                    "ora-versions": {
                                        "Attributes": {},
                                        "Nodes": {},
                                        "Table": {
                                            "KeyColumns": ["version"],
                                            "Rows": [
                                                {
                                                    "version": "version1",
                                                    "edition": "edition1",
                                                },
                                                {
                                                    "version": "version2",
                                                    "edition": "edition2",
                                                },
                                            ],
                                        },
                                    },
                                    "ora-foobar": {
                                        "Attributes": {},
                                        "Nodes": {},
                                        "Table": {
                                            "KeyColumns": ["foo"],
                                            "Rows": [
                                                {
                                                    "foo": "foo1",
                                                    "bar": "bar",
                                                },
                                                {
                                                    "foo": "foo2",
                                                    "bar": "bar",
                                                },
                                            ],
                                        },
                                    },
                                },
                                "Table": {},
                            },
                        },
                        "Table": {},
                    }
                ),
                "JOIN": {
                    "invoradataguardstats_db_unique": {"invoradataguardstats_db_unique": "name1"},
                    "invoraversions_edition": {"invoraversions_edition": "edition1"},
                },
            },
        ],
    ):
        assert set(row) == set(expected_row)

        assert row["site"] == expected_row["site"]
        assert row["host_name"] == expected_row["host_name"]
        assert row["invorainstance_sid"] == expected_row["invorainstance_sid"]
        assert row["invorainstance_version"] == expected_row["invorainstance_version"]
        assert row["JOIN"] == expected_row["JOIN"]
        assert row["host_inventory"] == expected_row["host_inventory"]
