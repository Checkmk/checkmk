#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Internal bakery API: the ``CoreBakelet`` plug-in type and its discovery prefix.

This is the ``internal`` variant of the per-domain bakery API (see the plugin
discovery reference in ``cmk.discover_plugins``). It is not exposed to
third-party plug-in authors; it carries the built-in ("core") bakelets that
ship with Checkmk.
"""

from ._artifacts import ABCBakeryFile as ABCBakeryFile
from ._artifacts import ABCFileContainer as ABCFileContainer
from ._artifacts import ABCYamlConfig as ABCYamlConfig
from ._artifacts import AgentFileLocator as AgentFileLocator
from ._artifacts import AgentInternalFileContainer as AgentInternalFileContainer
from ._artifacts import CustomFileContainer as CustomFileContainer
from ._artifacts import FileFromSite as FileFromSite
from ._artifacts import GeneratedBinaryFile as GeneratedBinaryFile
from ._artifacts import GeneratedTextFile as GeneratedTextFile
from ._artifacts import HomeFileContainer as HomeFileContainer
from ._artifacts import IntervalConfig as IntervalConfig
from ._artifacts import LibFileContainer as LibFileContainer
from ._artifacts import PluginConfigContainer as PluginConfigContainer
from ._artifacts import PluginContainer as PluginContainer
from ._artifacts import RootFileContainer as RootFileContainer
from ._artifacts import ScriptletHandle as ScriptletHandle
from ._artifacts import SystemBinaryContainer as SystemBinaryContainer
from ._artifacts import SystemConfigContainer as SystemConfigContainer
from ._artifacts import YamlEntry as YamlEntry
from ._artifacts import YamlItems as YamlItems
from ._artifacts import YamlPluginSettings as YamlPluginSettings
from ._artifacts import YamlStore as YamlStore
from ._common_config import AgentControllerTargetArch as AgentControllerTargetArch
from ._common_config import AgentPathsConfig as AgentPathsConfig
from ._common_config import CustomizeAgentPackageConfig as CustomizeAgentPackageConfig
from ._common_config import DeploymentConfig as DeploymentConfig
from ._common_config import DeploymentMode as DeploymentMode
from ._common_config import DeploymentModeProvider as DeploymentModeProvider
from ._common_config import DirectoryConfig as DirectoryConfig
from ._common_config import get_agent_controller_arch as get_agent_controller_arch
from ._common_config import get_unix_agent_paths_keeper as get_unix_agent_paths_keeper
from ._common_config import process_windows_file_container as process_windows_file_container
from ._common_config import SingleDirectoryConfig as SingleDirectoryConfig
from ._common_config import TargetPathsProvider as TargetPathsProvider
from ._common_config import UnixAgentPathsKeeper as UnixAgentPathsKeeper
from ._common_config import UnixMultipleDirectoryKeeper as UnixMultipleDirectoryKeeper
from ._common_config import UnixSingleDirectoryKeeper as UnixSingleDirectoryKeeper
from ._common_config import UserCreationStrategy as UserCreationStrategy
from ._common_config import UserDeploymentConfig as UserDeploymentConfig
from ._constants import AGENT_FILE_HEADER as AGENT_FILE_HEADER
from ._constants import ALL_OPSYSES as ALL_OPSYSES
from ._constants import LogicalPath as LogicalPath
from ._constants import PYTHON_MODULE_EXT as PYTHON_MODULE_EXT
from ._constants import ScriptType as ScriptType
from ._core_bakelet import CoreBakelet as CoreBakelet
from ._core_bakelet import CoreFilesFunction as CoreFilesFunction
from ._core_bakelet import CoreScriptletsFunction as CoreScriptletsFunction
from ._core_bakelet import CoreYamlConfigFunction as CoreYamlConfigFunction
from ._core_bakelet import entry_point_prefixes as entry_point_prefixes
from ._types import AgentConfig as AgentConfig
from ._types import AgentHash as AgentHash

__all__ = [
    "ABCBakeryFile",
    "ABCFileContainer",
    "ABCYamlConfig",
    "AGENT_FILE_HEADER",
    "ALL_OPSYSES",
    "AgentConfig",
    "AgentControllerTargetArch",
    "AgentFileLocator",
    "AgentHash",
    "AgentInternalFileContainer",
    "AgentPathsConfig",
    "CoreBakelet",
    "CoreFilesFunction",
    "CoreScriptletsFunction",
    "CoreYamlConfigFunction",
    "CustomFileContainer",
    "CustomizeAgentPackageConfig",
    "DeploymentConfig",
    "DeploymentMode",
    "DeploymentModeProvider",
    "DirectoryConfig",
    "FileFromSite",
    "GeneratedBinaryFile",
    "GeneratedTextFile",
    "HomeFileContainer",
    "IntervalConfig",
    "LibFileContainer",
    "LogicalPath",
    "PYTHON_MODULE_EXT",
    "PluginConfigContainer",
    "PluginContainer",
    "RootFileContainer",
    "ScriptType",
    "ScriptletHandle",
    "SingleDirectoryConfig",
    "SystemBinaryContainer",
    "SystemConfigContainer",
    "TargetPathsProvider",
    "UnixAgentPathsKeeper",
    "UnixMultipleDirectoryKeeper",
    "UnixSingleDirectoryKeeper",
    "UserCreationStrategy",
    "UserDeploymentConfig",
    "YamlEntry",
    "YamlItems",
    "YamlPluginSettings",
    "YamlStore",
    "entry_point_prefixes",
    "get_agent_controller_arch",
    "get_unix_agent_paths_keeper",
    "process_windows_file_container",
]
