#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: The scope of what is exposed here is *not* the same as the API exposed to the plugins
# for version 1, but these *are* the actual classes.
# This is confusing, and will be fixed for v2:w


from ._artifact_types import Plugin as Plugin
from ._artifact_types import PluginConfig as PluginConfig
from ._artifact_types import Scriptlet as Scriptlet
from ._artifact_types import SystemBinary as SystemBinary
from ._artifact_types import SystemConfig as SystemConfig
from ._artifact_types import WindowsConfigEntry as WindowsConfigEntry
from ._artifact_types import WindowsConfigItems as WindowsConfigItems
from ._artifact_types import WindowsGlobalConfigEntry as WindowsGlobalConfigEntry
from ._artifact_types import WindowsSystemConfigEntry as WindowsSystemConfigEntry
from ._constants import DebStep as DebStep
from ._constants import OS as OS
from ._constants import PkgStep as PkgStep
from ._constants import RpmStep as RpmStep
from ._constants import SolStep as SolStep
from ._constants import WindowsConfigContent as WindowsConfigContent
from ._function_types import BakeryPlugin as BakeryPlugin
from ._function_types import BakeryPluginName as BakeryPluginName
from ._function_types import create_bakery_plugin as create_bakery_plugin
from ._function_types import FileGenerator as FileGenerator
from ._function_types import FilesFunction as FilesFunction
from ._function_types import ScriptletGenerator as ScriptletGenerator
from ._function_types import ScriptletsFunction as ScriptletsFunction
from ._function_types import WindowsConfigFunction as WindowsConfigFunction
from ._function_types import WindowsConfigGenerator as WindowsConfigGenerator
