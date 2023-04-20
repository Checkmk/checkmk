#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.plugins.dashboard


def test_pre_21_plugin_api_names() -> None:
    for name in (
        "ABCFigureDashlet",
        "builtin_dashboards",
        "Dashlet",
        "dashlet_registry",
        "GROW",
        "IFrameDashlet",
        "MAX",
    ):
        assert name in cmk.gui.plugins.dashboard.__dict__
