#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
+---------------------------------------------------------+
|              Achtung Alles Lookenskeepers!              |
|              =============================              |
|                                                         |
| The extend of this API is well documented, and the      |
| result of careful negotiation. It must not be changed!  |
|                                                         |
+---------------------------------------------------------+
"""

from cmk.bakery import v2_alpha as v2


def test_v1_namespace() -> None:
    assert {v for v in vars(v2) if not v.startswith("_")} == {
        "BakeryPlugin",
        "DebStep",
        "entry_point_prefixes",
        "FileGenerator",
        "no_op_parser",
        "OS",
        "PkgStep",
        "Plugin",
        "PluginConfig",
        "RpmStep",
        "Scriptlet",
        "ScriptletGenerator",
        "Secret",
        "SolStep",
        "SystemBinary",
        "SystemConfig",
        "WindowsConfigContent",
        "WindowsConfigEntry",
        "WindowsConfigGenerator",
        "WindowsConfigItems",
        "WindowsGlobalConfigEntry",
        "WindowsSystemConfigEntry",
    }
