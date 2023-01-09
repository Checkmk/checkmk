#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.type_defs import PainterSpec, RawPainterSpec, VisualLinkSpec


@pytest.mark.parametrize(
    "raw_painter_spec, expected_painter_spec",
    [
        pytest.param(
            (
                "name",
                "view_name",
            ),
            PainterSpec(
                name="name",
                parameters=None,
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
            PainterSpec(
                name="name",
                parameters=None,
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
            PainterSpec(
                name="name",
                parameters=None,
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
            PainterSpec(
                name="name",
                parameters=None,
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
            PainterSpec(
                name="name",
                parameters={"column_title": "another column title"},
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
            PainterSpec(
                name="name",
                parameters={"column_title": "another column title"},
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
            PainterSpec(
                name="name",
                parameters=None,
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
def test_painter_spec_from_raw(
    raw_painter_spec: tuple | RawPainterSpec,
    expected_painter_spec: PainterSpec,
) -> None:
    assert PainterSpec.from_raw(raw_painter_spec) == expected_painter_spec


@pytest.mark.parametrize(
    "painter_spec, expected_raw_painter_spec",
    [
        pytest.param(
            PainterSpec(
                name="name",
                parameters={"column_title": "another column title"},
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
            PainterSpec(
                name="name",
                parameters=None,
                link_spec=None,
                tooltip=None,
                join_index=None,
                column_title=None,
            ),
            {
                "name": "name",
                "parameters": None,
                "link_spec": None,
                "tooltip": None,
                "join_index": None,
                "column_title": None,
                "column_type": "column",
            },
        ),
    ],
)
def test_painter_spec_to_raw(
    painter_spec: PainterSpec,
    expected_raw_painter_spec: RawPainterSpec,
) -> None:
    assert painter_spec.to_raw() == expected_raw_painter_spec
