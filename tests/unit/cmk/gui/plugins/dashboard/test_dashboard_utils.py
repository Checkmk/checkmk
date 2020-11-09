#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from cmk.gui.plugins.dashboard import utils


@pytest.mark.parametrize(
    "entry, result",
    [
        pytest.param(
            {
                'type': 'pnpgraph',
                'show_legend': True,
                'show_service': True,
                'single_infos': [],
            }, {
                'graph_render_options': {
                    'show_legend': True
                },
                'single_infos': ['service', 'host'],
                'title_format': ['plain', 'add_host_name', 'add_service_description'],
                'type': 'pnpgraph'
            },
            id="->1.5.0i2->2.0.0i2 pnpgraph"),
        pytest.param(
            {
                'type': 'pnpgraph',
                'graph_render_options': {
                    'show_legend': False,
                    'show_title': True,
                    'title_format': 'plain',
                },
                'single_infos': ['host', 'service'],
            }, {
                'graph_render_options': {
                    'show_legend': False,
                },
                'single_infos': ['host', 'service'],
                'title_format': ['plain'],
                'type': 'pnpgraph'
            },
            id="1.6.0->2.0.0i1 pnpgraph"),
    ],
)
def test_transform_dashlets_mut(entry, result):
    assert utils._transform_dashlets_mut(entry) == result
