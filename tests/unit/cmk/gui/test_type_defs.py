#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.type_defs import (
    ColumnSpec,
    PainterParameters,
    RawColumnSpec,
    RawLegacyColumnSpec,
    VisualLinkSpec,
)


@pytest.mark.parametrize(
    "raw_column_spec, expected_column_spec",
    [
        pytest.param(
            (
                "name",
                "view_name",
            ),
            ColumnSpec(
                name="name",
                parameters=PainterParameters(),
                link_spec=VisualLinkSpec(
                    type_name="views",
                    name="view_name",
                ),
                tooltip=None,
                join_index=None,
                column_title=None,
            ),
        ),
        pytest.param(
            (
                "name",
                "view_name",
                "tooltip",
            ),
            ColumnSpec(
                name="name",
                parameters=PainterParameters(),
                link_spec=VisualLinkSpec(
                    type_name="views",
                    name="view_name",
                ),
                tooltip="tooltip",
                join_index=None,
                column_title=None,
            ),
        ),
        pytest.param(
            (
                "name",
                "view_name",
                "tooltip",
                "join index",
            ),
            ColumnSpec(
                name="name",
                parameters=PainterParameters(),
                link_spec=VisualLinkSpec(
                    type_name="views",
                    name="view_name",
                ),
                tooltip="tooltip",
                join_index="join index",
                column_title=None,
            ),
        ),
        pytest.param(
            (
                "name",
                "view_name",
                "tooltip",
                "join index",
                "column title",
            ),
            ColumnSpec(
                name="name",
                parameters=PainterParameters(),
                link_spec=VisualLinkSpec(
                    type_name="views",
                    name="view_name",
                ),
                tooltip="tooltip",
                join_index="join index",
                column_title="column title",
            ),
        ),
        pytest.param(
            (
                ("name", {"column_title": "another column title"}),
                ("reports", "view_name"),
                "",
                None,
                None,
            ),
            ColumnSpec(
                name="name",
                parameters=PainterParameters(column_title="another column title"),
                link_spec=VisualLinkSpec(
                    type_name="reports",
                    name="view_name",
                ),
                tooltip=None,
                join_index=None,
                column_title=None,
            ),
        ),
        pytest.param(
            {
                "name": "name",
                "parameters": {"column_title": "another column title"},
                "link_spec": "view_name",
                "tooltip": "tooltip",
                "join_index": "join index",
                "column_title": "column title",
            },
            ColumnSpec(
                name="name",
                parameters=PainterParameters(column_title="another column title"),
                link_spec=VisualLinkSpec(
                    type_name="views",
                    name="view_name",
                ),
                tooltip="tooltip",
                join_index="join index",
                column_title="column title",
            ),
        ),
        pytest.param(
            {
                "name": "name",
                "parameters": None,
                "link_spec": ("reports", "view_name"),
                "tooltip": "",
                "join_index": None,
                "column_title": None,
            },
            ColumnSpec(
                name="name",
                parameters=PainterParameters(),
                link_spec=VisualLinkSpec(
                    type_name="reports",
                    name="view_name",
                ),
                tooltip=None,
                join_index=None,
                column_title=None,
            ),
        ),
    ],
)
def test_column_spec_from_raw(
    raw_column_spec: tuple | RawLegacyColumnSpec,
    expected_column_spec: ColumnSpec,
) -> None:
    assert ColumnSpec.from_raw(raw_column_spec) == expected_column_spec


@pytest.mark.parametrize(
    "column_spec, expected_raw_column_spec",
    [
        pytest.param(
            ColumnSpec(
                name="name",
                parameters=PainterParameters(column_title="another column title"),
                link_spec=VisualLinkSpec(
                    type_name="views",
                    name="view_name",
                ),
                tooltip="tooltip",
                join_index="join index",
                column_title="column title",
            ),
            {
                "name": "name",
                "parameters": {"column_title": "another column title"},
                "link_spec": ("views", "view_name"),
                "tooltip": "tooltip",
                "join_index": "join index",
                "column_title": "column title",
                "column_type": "join_column",
            },
        ),
        pytest.param(
            ColumnSpec(
                name="name",
                parameters=PainterParameters(),
                link_spec=None,
                tooltip=None,
                join_index=None,
                column_title=None,
            ),
            {
                "name": "name",
                "parameters": {},
                "link_spec": None,
                "tooltip": None,
                "join_index": None,
                "column_title": None,
                "column_type": "column",
            },
        ),
    ],
)
def test_column_spec_to_raw(
    column_spec: ColumnSpec,
    expected_raw_column_spec: RawColumnSpec,
) -> None:
    assert column_spec.to_raw() == expected_raw_column_spec
