#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.metrics import valuespecs


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
def test_transform_graph_render_options_title_format(entry, result):
    assert valuespecs.transform_graph_render_options_title_format(entry) == result


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
def test_transform_graph_render_options(entry, result):
    assert valuespecs.transform_graph_render_options(entry) == result
