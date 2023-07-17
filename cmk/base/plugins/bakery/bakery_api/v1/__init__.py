#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shlex

# For an explanation of what is what see comments in __all__definition at the end
from cmk.utils import password_store

from cmk.base.api.bakery.artifact_types import (
    Plugin,
    PluginConfig,
    Scriptlet,
    SystemBinary,
    SystemConfig,
    WindowsConfigEntry,
    WindowsConfigItems,
    WindowsGlobalConfigEntry,
    WindowsSystemConfigEntry,
)
from cmk.base.api.bakery.constants import DebStep, OS, RpmStep, SolStep, WindowsConfigContent
from cmk.base.api.bakery.function_types import (
    FileGenerator,
    ScriptletGenerator,
    WindowsConfigGenerator,
)

from . import register


def quote_shell_string(s: str) -> str:
    """
    Quote a string for use in a shell command.

    This function is deprecated and is just an alias for `shlex.quote`. It will remain available in
    bakery API v1, but may be removed in a future version of the API. It is recommended to use
    `shlex.quote` instead.
    """
    return shlex.quote(s)


__all__ = [
    # registration
    "register",
    # Identifiers
    "OS",
    "DebStep",
    "RpmStep",
    "SolStep",
    # File artifacts
    "Plugin",
    "PluginConfig",
    "SystemConfig",
    "SystemBinary",
    # Scriplet artifact
    "Scriptlet",
    # Windows Config artifacts
    "WindowsConfigEntry",
    "WindowsConfigItems",
    "WindowsGlobalConfigEntry",
    "WindowsSystemConfigEntry",
    # Types for Type annotations
    "FileGenerator",
    "ScriptletGenerator",
    "WindowsConfigGenerator",
    "WindowsConfigContent",
    # utils
    "quote_shell_string",
    "password_store",
]
