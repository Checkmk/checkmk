#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._loader import load_graphing_plugins


def test_load_graphing_plugins() -> None:
    discovered_graphing_plugins = load_graphing_plugins()
    assert not discovered_graphing_plugins.errors
    assert discovered_graphing_plugins.plugins
