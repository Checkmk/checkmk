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

from ._artifacts import ABCYamlConfig as ABCYamlConfig
from ._artifacts import ScriptletHandle as ScriptletHandle
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
from ._common_config import SingleDirectoryConfig as SingleDirectoryConfig
from ._common_config import TargetPathsProvider as TargetPathsProvider
from ._common_config import UnixAgentPathsKeeper as UnixAgentPathsKeeper
from ._common_config import UnixMultipleDirectoryKeeper as UnixMultipleDirectoryKeeper
from ._common_config import UnixSingleDirectoryKeeper as UnixSingleDirectoryKeeper
from ._common_config import UserCreationStrategy as UserCreationStrategy
from ._common_config import UserDeploymentConfig as UserDeploymentConfig
from ._constants import AGENT_FILE_HEADER as AGENT_FILE_HEADER
from ._constants import ALL_OPSYSES as ALL_OPSYSES
from ._constants import CUSTOM_FILE_SUBDIRS as CUSTOM_FILE_SUBDIRS
from ._constants import LogicalPath as LogicalPath
from ._constants import PYTHON_MODULE_EXT as PYTHON_MODULE_EXT
from ._constants import ScriptType as ScriptType
from ._core_bakelet import CoreBakelet as CoreBakelet
from ._core_bakelet import CoreFilesFunction as CoreFilesFunction
from ._core_bakelet import CoreScriptletsFunction as CoreScriptletsFunction
from ._core_bakelet import CoreYamlConfigFunction as CoreYamlConfigFunction
from ._core_bakelet import entry_point_prefixes as entry_point_prefixes
from ._recipes import BinaryFile as BinaryFile
from ._recipes import CustomFile as CustomFile
from ._recipes import HashDependency as HashDependency
from ._recipes import PluginExecution as PluginExecution
from ._recipes import SiteFile as SiteFile
from ._recipes import TextFile as TextFile
from ._types import AgentConfig as AgentConfig
from ._types import AgentHash as AgentHash

__all__ = [
    "ABCYamlConfig",
    "AGENT_FILE_HEADER",
    "ALL_OPSYSES",
    "AgentConfig",
    "AgentControllerTargetArch",
    "AgentHash",
    "AgentPathsConfig",
    "BinaryFile",
    "CoreBakelet",
    "CoreFilesFunction",
    "CoreScriptletsFunction",
    "CoreYamlConfigFunction",
    "CUSTOM_FILE_SUBDIRS",
    "CustomFile",
    "CustomizeAgentPackageConfig",
    "DeploymentConfig",
    "DeploymentMode",
    "DeploymentModeProvider",
    "DirectoryConfig",
    "HashDependency",
    "LogicalPath",
    "PYTHON_MODULE_EXT",
    "PluginExecution",
    "ScriptType",
    "ScriptletHandle",
    "SiteFile",
    "SingleDirectoryConfig",
    "TargetPathsProvider",
    "TextFile",
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
]
