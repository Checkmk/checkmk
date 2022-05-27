#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.logged_in import user
from cmk.gui.plugins.views.utils import (
    _encode_sorter_url,
    _parse_url_sorters,
    Cell,
    group_value,
    Painter,
    painter_registry,
    register_painter,
    replace_action_url_macros,
    SorterSpec,
)
from cmk.gui.type_defs import PainterSpec
from cmk.gui.views import View


@pytest.mark.parametrize(
    "url, sorters",
    [
        (
            "-svcoutput,svc_perf_val01,svc_metrics_hist",
            [("svcoutput", True), ("svc_perf_val01", False), ("svc_metrics_hist", False)],
        ),
        (
            "sitealias,perfometer~CPU utilization,site",
            [("sitealias", False), ("perfometer", False, "CPU utilization"), ("site", False)],
        ),
    ],
)
def test_url_sorters_parse_encode(url, sorters):
    sorters = [SorterSpec(*s) for s in sorters]
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


def test_group_value() -> None:
    def rendr(row) -> tuple[str, str]:
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

    painter: Painter = painter_registry["tag_painter"]()
    dummy_cell: Cell = Cell(View("", {}, {}), PainterSpec(painter.ident))

    assert group_value({"host_tags": {"networking": "dmz"}}, [dummy_cell]) == ("dmz",)
