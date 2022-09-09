#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable

import pytest

import cmk.gui.plugins.views.utils as utils
from cmk.gui.logged_in import user
from cmk.gui.plugins.views.utils import (
    _encode_sorter_url,
    Cell,
    group_value,
    Painter,
    PainterRegistry,
    replace_action_url_macros,
)
from cmk.gui.type_defs import PainterSpec, SorterSpec
from cmk.gui.views import _parse_url_sorters


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


def test_group_value(monkeypatch) -> None:  # type:ignore[no-untyped-def]
    monkeypatch.setattr(utils, "painter_registry", PainterRegistry())

    def rendr(row) -> tuple[str, str]:  # type:ignore[no-untyped-def]
        return ("abc", "xyz")

    utils.register_painter(
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

    painter: Painter = utils.painter_registry["tag_painter"]()
    dummy_cell: Cell = Cell({}, None, PainterSpec(name=painter.ident))

    assert group_value({"host_tags": {"networking": "dmz"}}, [dummy_cell]) == ("dmz",)
