#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.gui.dashboard.dashlet.figure_dashlet import ABCFigureDashlet


@pytest.mark.parametrize(
    "entry, result",
    [
        pytest.param(
            {"svc_status_display": {"some": "content"}, "some": "other stuff"},
            {"status_display": {"some": "content"}, "some": "other stuff"},
            id="2.0.0->2.1.0i1",
        ),
    ],
)
def test_migrate_dashlet_status_display(entry: dict[str, object], result: str) -> None:
    assert ABCFigureDashlet._migrate_vs(entry) == result
