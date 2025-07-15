#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.ccc.user import UserId

from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.http import request, response
from cmk.gui.logged_in import user
from cmk.gui.painter.v0 import Cell, Painter, PainterRegistry, register_painter, registry
from cmk.gui.painter.v0.helpers import RenderLink, replace_action_url_macros
from cmk.gui.painter_options import PainterOptions
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import ColumnSpec, Row, SorterSpec, ViewSpec
from cmk.gui.views.layout import group_value
from cmk.gui.views.page_show_view import _parse_url_sorters
from cmk.gui.views.sort_url import _encode_sorter_url
from cmk.gui.views.store import multisite_builtin_views


@pytest.fixture(name="view_spec")
def view_spec_fixture(request_context: None) -> ViewSpec:
    return multisite_builtin_views["allhosts"]


@pytest.mark.parametrize(
    "url, sorters",
    [
        (
            "-svcoutput,svc_perf_val01,svc_metrics_hist",
            [
                SorterSpec(sorter="svcoutput", negate=True),
                SorterSpec(sorter="svc_perf_val01", negate=False),
                SorterSpec(sorter="svc_metrics_hist", negate=False),
            ],
        ),
        (
            "sitealias,perfometer~CPU utilization,site",
            [
                SorterSpec(sorter="sitealias", negate=False),
                SorterSpec(sorter="perfometer", negate=False, join_key="CPU utilization"),
                SorterSpec(sorter="site", negate=False),
            ],
        ),
    ],
)
def test_url_sorters_parse_encode(url: str, sorters: Sequence[SorterSpec]) -> None:
    assert _parse_url_sorters(sorters, [], url) == sorters
    assert _encode_sorter_url(sorters) == url


@pytest.mark.parametrize(
    "url, what, row, result",
    [
        (
            "$HOSTNAME$_$HOSTADDRESS$_$USER_ID$_$HOSTNAME_URL_ENCODED$",
            "host",
            {
                "host_name": "host",
                "host_address": "1.2.3",
            },
            "host_1.2.3_user_host",
        ),
        (
            "$SERVICEDESC$",
            "service",
            {
                "host_name": "host",
                "host_address": "1.2.3",
                "service_description": "service",
            },
            "service",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_replace_action_url_macros(
    monkeypatch: pytest.MonkeyPatch, url: str, what: str, row: Row, result: str
) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "id", UserId("user"))
        assert replace_action_url_macros(url, what, row) == result


def test_group_value(monkeypatch: pytest.MonkeyPatch, view_spec: ViewSpec) -> None:
    monkeypatch.setattr(registry, "painter_registry", painter_registry := PainterRegistry())

    def rendr(row: Row) -> tuple[str, str]:
        return ("abc", "xyz")

    register_painter(
        "tag_painter",
        {
            "title": "Tag painter",
            "short": "tagpaint",
            "columns": ["x"],
            "sorter": "aaaa",
            "options": ["opt1"],
            "printable": False,
            "paint": rendr,
            "groupby": "dmz",
        },
    )

    painter: Painter = painter_registry["tag_painter"](
        config=active_config,
        request=request,
        painter_options=PainterOptions.get_instance(),
        theme=theme,
        url_renderer=RenderLink(request, response, display_options),
    )
    dummy_cell: Cell = Cell(ColumnSpec(name=painter.ident), None, painter_registry)

    assert group_value({"host_tags": {"networking": "dmz"}}, [dummy_cell]) == ("dmz",)
