#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.gui.graphing import GraphDisplayConfigHTML, TemplateGraphSpecification
from cmk.gui.graphing._frontend import STATIC_INTERACTION
from cmk.gui.type_defs import SizePT
from cmk.gui.views import graph as graph_views
from cmk.shared_typing.cmk_time_series_graph import Interaction
from cmk.web.utils.html import HTML

_SPECIFICATION = TemplateGraphSpecification(
    site=None,
    host_name=HostName("host"),
    service_description="CPU load",
)

_EVERYTHING_OFF = GraphDisplayConfigHTML(
    show_title=False,
    show_graph_time=False,
    show_legend=False,
    show_vertical_axis=False,
    show_time_axis=False,
    show_controls=False,
    show_pin=False,
)

# The dialog's plain on/off options; the others are checked individually below.
_ON_OFF_OPTIONS = (
    "show_title",
    "show_graph_time",
    "show_legend",
    "show_vertical_axis",
    "show_time_axis",
)


def _forwarded(
    monkeypatch: pytest.MonkeyPatch,
    display_config: GraphDisplayConfigHTML,
    *,
    mobile: bool = False,
) -> Mapping[str, object]:
    """Recorded rather than rendered: building the group would resolve the host's metric names
    over livestatus."""
    recorded: dict[str, object] = {}

    def _record(_specification: object, **kwargs: object) -> HTML:
        recorded.update(kwargs)
        return HTML.empty()

    monkeypatch.setattr(graph_views, "render_engine_graph_group", _record)
    graph_views._render_engine_graph_group(
        {"host_name": "host", "service_description": "CPU load"},
        _SPECIFICATION,
        display_config,
        graph_size=(70.0, 16.0),
        raw_time_range=(1_000, 2_000),
        debug=False,
        mobile=mobile,
    )
    return recorded


def _interaction_of(forwarded: Mapping[str, object]) -> Interaction:
    interaction = forwarded["interaction"]
    assert isinstance(interaction, Interaction)
    return interaction


@pytest.mark.parametrize("option", _ON_OFF_OPTIONS)
def test_a_display_option_switched_off_reaches_the_engine(
    monkeypatch: pytest.MonkeyPatch, option: str
) -> None:
    assert _forwarded(monkeypatch, _EVERYTHING_OFF)[option] is False


@pytest.mark.parametrize("option", _ON_OFF_OPTIONS)
def test_a_display_option_left_on_reaches_the_engine(
    monkeypatch: pytest.MonkeyPatch, option: str
) -> None:
    assert _forwarded(monkeypatch, GraphDisplayConfigHTML())[option] is True


def test_the_burger_menu_follows_the_controls_option(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _interaction_of(_forwarded(monkeypatch, _EVERYTHING_OFF)).burger == "disabled"
    assert _interaction_of(_forwarded(monkeypatch, GraphDisplayConfigHTML())).burger == "enabled"


def test_the_pin_follows_the_pin_option(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _interaction_of(_forwarded(monkeypatch, _EVERYTHING_OFF)).pin == "disabled"
    assert _interaction_of(_forwarded(monkeypatch, GraphDisplayConfigHTML())).pin == "enabled"


def test_the_configured_vertical_axis_width_reaches_the_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forwarded = _forwarded(
        monkeypatch, GraphDisplayConfigHTML(vertical_axis_width=("explicit", SizePT(40.0)))
    )

    assert forwarded["vertical_axis_width"] == ("explicit", 40.0)


def test_mobile_stays_static_even_with_the_controls_switched_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forwarded = _forwarded(monkeypatch, GraphDisplayConfigHTML(), mobile=True)

    assert _interaction_of(forwarded) == STATIC_INTERACTION
