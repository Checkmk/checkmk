#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest

from cmk.gui.type_defs import (
    _RawColumnSpec,
    _RawLegacyColumnSpec,
    ColumnSpec,
    PainterParameters,
    VisualLinkSpec,
)


@pytest.mark.parametrize(
    "raw_column_spec, expected_column_spec, expected_column_type",
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
                join_value=None,
                column_title=None,
                _column_type="column",
            ),
            "column",
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
                join_value=None,
                column_title=None,
                _column_type="column",
            ),
            "column",
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
                join_value="join index",
                column_title=None,
                _column_type="join_column",
            ),
            "join_column",
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
                join_value="join index",
                column_title="column title",
                _column_type="join_column",
            ),
            "join_column",
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
                join_value=None,
                column_title=None,
                _column_type="column",
            ),
            "column",
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
                join_value="join index",
                column_title="column title",
                _column_type=None,
            ),
            "join_column",
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
                join_value=None,
                column_title=None,
                _column_type=None,
            ),
            "column",
        ),
        pytest.param(
            {
                "name": "name",
                "parameters": None,
                "link_spec": ("reports", "view_name"),
                "tooltip": "",
                "join_index": "join index",
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
                join_value="join index",
                column_title=None,
                _column_type=None,
            ),
            "join_column",
        ),
        pytest.param(
            {
                "name": "name",
                "parameters": None,
                "link_spec": ("reports", "view_name"),
                "tooltip": "",
                "join_index": "join index",
                "column_title": None,
                "column_type": "join_column",
            },
            ColumnSpec(
                name="name",
                parameters=PainterParameters(),
                link_spec=VisualLinkSpec(
                    type_name="reports",
                    name="view_name",
                ),
                tooltip=None,
                join_value="join index",
                column_title=None,
                _column_type="join_column",
            ),
            "join_column",
        ),
        pytest.param(
            {
                "name": "name",
                "parameters": None,
                "link_spec": ("reports", "view_name"),
                "tooltip": "",
                "join_index": None,
                "column_title": None,
                "column_type": "column",
            },
            ColumnSpec(
                name="name",
                parameters=PainterParameters(),
                link_spec=VisualLinkSpec(
                    type_name="reports",
                    name="view_name",
                ),
                tooltip=None,
                join_value=None,
                column_title=None,
                _column_type="column",
            ),
            "column",
        ),
    ],
)
def test_column_spec_from_raw(
    raw_column_spec: _RawColumnSpec | _RawLegacyColumnSpec | tuple,
    expected_column_spec: ColumnSpec,
    expected_column_type: Literal["column", "join_column"],
) -> None:
    column_spec = ColumnSpec.from_raw(raw_column_spec)
    assert column_spec == expected_column_spec
    assert column_spec.column_type == expected_column_type
    assert column_spec.column_type == expected_column_spec.column_type


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
                join_value="join index",
                column_title="column title",
            ),
            {
                "name": "name",
                "parameters": {"column_title": "another column title"},
                "link_spec": ("views", "view_name"),
                "tooltip": "tooltip",
                "join_value": "join index",
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
                join_value=None,
                column_title=None,
            ),
            {
                "name": "name",
                "parameters": {},
                "link_spec": None,
                "tooltip": None,
                "join_value": None,
                "column_title": None,
                "column_type": "column",
            },
        ),
    ],
)
def test_column_spec_to_raw(
    column_spec: ColumnSpec,
    expected_raw_column_spec: _RawColumnSpec,
) -> None:
    assert column_spec.to_raw() == expected_raw_column_spec
