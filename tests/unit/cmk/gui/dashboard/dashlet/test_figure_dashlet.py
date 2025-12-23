#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.dashboard.dashlet.figure_dashlet import ABCFigureDashlet
from cmk.gui.dashboard.dashlet.registry import dashlet_registry
from cmk.gui.dashboard.page_figure_widget import GENERATOR_BY_FIGURE_TYPE
from tests.testlib.common.repo import is_non_free_repo


@pytest.mark.skipif(
    is_non_free_repo(), reason="GENERATOR_BY_FIGURE_TYPE holds CRE-only figure types"
)
def test_generate_response_data_mapping() -> None:
    all_figure_types = {
        dashlet.type_name()
        for dashlet in dashlet_registry.values()
        if issubclass(dashlet, ABCFigureDashlet)
    }
    assert set(GENERATOR_BY_FIGURE_TYPE.keys()) == all_figure_types
