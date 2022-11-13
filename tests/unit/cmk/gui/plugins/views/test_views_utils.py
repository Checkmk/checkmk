#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable

import pytest

from cmk.gui.logged_in import user
from cmk.gui.painters.v0 import base as painter_base
from cmk.gui.painters.v0.base import _encode_sorter_url, Cell, Painter, PainterRegistry
from cmk.gui.painters.v0.helpers import replace_action_url_macros
from cmk.gui.type_defs import PainterSpec, Row, SorterSpec, ViewSpec
from cmk.gui.view_store import multisite_builtin_views
from cmk.gui.views.layout import group_value
from cmk.gui.views.page_show_view import _parse_url_sorters


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
def test_url_sorters_parse_encode(url: str, sorters: Iterable[SorterSpec]) -> None:
    assert _parse_url_sorters(url) == sorters
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
def test_replace_action_url_macros(
    monkeypatch,
    request_context,
    url,
    what,
    row,
    result,
):
    monkeypatch.setattr(
        user,
        "id",
        "user",
    )
    assert replace_action_url_macros(url, what, row) == result


def test_group_value(monkeypatch: pytest.MonkeyPatch, view_spec: ViewSpec) -> None:
    monkeypatch.setattr(painter_base, "painter_registry", PainterRegistry())

    def rendr(row: Row) -> tuple[str, str]:
        return ("abc", "xyz")

    painter_base.register_painter(
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

    painter: Painter = painter_base.painter_registry["tag_painter"]()
    dummy_cell: Cell = Cell(view_spec, None, PainterSpec(name=painter.ident))

    assert group_value({"host_tags": {"networking": "dmz"}}, [dummy_cell]) == ("dmz",)
