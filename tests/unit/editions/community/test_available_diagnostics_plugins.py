#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.diagnostics.engine import load_diagnostics_plugins


def test_available_diagnostics_plugins() -> None:
    discovered = load_diagnostics_plugins(raise_errors=True)
    assert {
        plugin.name: (plugin.topic, plugin.sensitivity, plugin.always)
        for plugin in discovered.plugins.values()
    } == {}
