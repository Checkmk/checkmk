#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Literal

import pytest

from cmk.gui.graphing._valuespecs import (
    _vs_show_title,
    migrate_graph_render_options,
    migrate_graph_render_options_title_format,
    migrate_graph_render_options_title_format_from_disk,
    vs_graph_render_option_elements,
)
from cmk.gui.http import request
from cmk.gui.valuespec import DropdownChoice, ValueSpec


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


def test_migrate_graph_render_options_title_format_rejects_unknown_entries() -> None:
    with pytest.raises(ValueError):
        migrate_graph_render_options_title_format_from_disk(["plain", "bogus"])


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


def test_graph_render_options_offer_the_legacy_renderer_options_by_default() -> None:
    # Other callers still render all of these, so they may only be dropped where one asks for it.
    elements = dict(vs_graph_render_option_elements())
    assert {"font_size", "title_format", "show_time_range_previews", "fixed_timerange"} <= set(
        elements
    )
    assert "inline" in _show_title_choice_ids(elements)


def test_graph_render_options_can_drop_the_inline_title() -> None:
    elements = dict(vs_graph_render_option_elements(with_inline_title=False))
    assert _show_title_choice_ids(elements) == [False, True]


def test_graph_title_without_the_inline_choice_tolerates_a_stored_inline_title(
    request_context: None,
) -> None:
    show_title = _vs_show_title(True, with_inline_title=False)
    request.set_var("title", "inline")
    assert show_title.from_html_vars("title") is True


def _show_title_choice_ids(elements: Mapping[str, ValueSpec[object]]) -> list[object]:
    show_title = elements["show_title"]
    assert isinstance(show_title, DropdownChoice)
    return [choice_id for choice_id, _title in show_title.choices()]
