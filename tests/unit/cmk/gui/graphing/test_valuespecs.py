#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal

import pytest

from cmk.gui.graphing._valuespecs import (
    migrate_graph_render_options,
    migrate_graph_render_options_title_format,
)


@pytest.mark.parametrize(
    "entry, result",
    [
        pytest.param(
            "add_host_name", ["plain", "add_host_name"], id="->1.5.0i2->2.0.0i1 pnp_graph reportlet"
        ),
        pytest.param("plain", ["plain"], id="1.5.0i2->2.0.0i1 direct plain title"),
        pytest.param(
            ("add_title_infos", ["add_host_alias", "add_service_description"]),
            ["plain", "add_host_alias", "add_service_description"],
            id="1.5.0i2->2.0.0i1 infos from CascadingDropdown",
        ),
        pytest.param(["add_host_name"], ["add_host_name"], id="2.0.0i1 fixpoint"),
        pytest.param(["add_host_name"], ["add_host_name"], id="2.0.0i1 fixpoint"),
        pytest.param(
            ["add_title_infos", ["add_host_name", "add_service_description"]],
            ["plain", "add_host_name", "add_service_description"],
            id="Format from JSON request CMK-6339",
        ),
    ],
)
def test_migrate_graph_render_options_title_format(
    entry: (
        Literal["plain"]
        | Literal["add_host_name"]
        | Literal["add_host_alias"]
        | tuple[
            Literal["add_title_infos"],
            list[
                Literal["add_host_name"]
                | Literal["add_host_alias"]
                | Literal["add_service_description"]
            ],
        ]
    ),
    result: Sequence[str],
) -> None:
    assert migrate_graph_render_options_title_format(entry) == result


@pytest.mark.parametrize(
    "entry, result",
    [
        pytest.param({}, {}, id="No fill defaults"),
        pytest.param(
            {"show_service": True},
            {"title_format": ["plain", "add_host_name", "add_service_description"]},
            id="->1.5.0i2->2.0.0i1 show_service to title format",
        ),
        pytest.param(
            {"title_format": "plain"},
            {"title_format": ["plain"]},
            id="1.5.0i2->2.0.0i1 title format DropdownChoice to ListChoice",
        ),
        pytest.param(
            {"title_format": ["plain"]}, {"title_format": ["plain"]}, id="2.0.0i1 fixpoint"
        ),
    ],
)
def test_migrate_graph_render_options(
    entry: Mapping[str, object], result: Mapping[str, Sequence[str]]
) -> None:
    assert migrate_graph_render_options(entry) == result
