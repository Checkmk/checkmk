#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.painter_options import painter_option_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_painter_options() -> None:
    assert sorted(painter_option_registry) == [
        "aggr_expand",
        "aggr_onlydiff",
        "aggr_onlyproblems",
        "aggr_treetype",
        "aggr_wrap",
        "graph_render_options",
        "matrix_omit_uniform",
        "num_columns",
        "pnp_timerange",
        "refresh",
        "show_internal_graph_and_metric_ids",
        "show_internal_tree_paths",
        "ts_date",
        "ts_format",
    ]
