#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ._active_check import execute_check_discovery
from ._autochecks import (
    AutocheckServiceWithNodes,
    AutochecksManager,
    AutochecksStore,
    merge_cluster_autochecks,
    remove_autochecks_of_host,
    set_autochecks_for_effective_host,
    set_autochecks_of_cluster,
    set_autochecks_of_real_hosts,
)
from ._autodiscovery import (
    autodiscovery,
    automation_discovery,
    DiscoveryReport,
    get_host_services_by_host_name,
    TransitionCounter,
)
from ._commandline import commandline_discovery
from ._filters import RediscoveryParameters
from ._host_labels import analyse_cluster_labels, discover_host_labels, HostLabelPlugin
from ._params import ABCDiscoveryConfig, DiscoveryCheckParameters, get_plugin_parameters
from ._preview import CheckPreview, CheckPreviewEntry, get_check_preview
from ._services import analyse_services, discover_services, find_plugins
from ._utils import (
    DiscoveryMode,
    DiscoverySettingFlags,
    DiscoverySettings,
    DiscoveryValueSpecModel,
    QualifiedDiscovery,
)

__all__ = [
    "analyse_cluster_labels",
    "analyse_services",
    "AutocheckServiceWithNodes",
    "AutochecksManager",
    "AutochecksStore",
    "autodiscovery",
    "automation_discovery",
    "CheckPreview",
    "CheckPreviewEntry",
    "ABCDiscoveryConfig",
    "commandline_discovery",
    "discover_host_labels",
    "discover_services",
    "DiscoveryCheckParameters",
    "DiscoveryMode",  # in the process of being replaced by DiscoverySettings
    "DiscoverySettings",
    "DiscoverySettingFlags",
    "DiscoveryValueSpecModel",
    "DiscoveryReport",
    "execute_check_discovery",
    "find_plugins",
    "get_check_preview",
    "get_plugin_parameters",
    "get_host_services_by_host_name",
    "HostLabelPlugin",
    "QualifiedDiscovery",
    "RediscoveryParameters",
    "remove_autochecks_of_host",
    "TransitionCounter",
    "set_autochecks_of_cluster",
    "set_autochecks_of_real_hosts",
    "set_autochecks_for_effective_host",
    "merge_cluster_autochecks",
]
