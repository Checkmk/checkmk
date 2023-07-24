#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ._autochecks import (
    AutocheckEntry,
    AutocheckServiceWithNodes,
    AutochecksManager,
    AutochecksStore,
    remove_autochecks_of_host,
    set_autochecks_of_cluster,
    set_autochecks_of_real_hosts,
)
from ._autodiscovery import autodiscovery, automation_discovery, DiscoveryResult, get_host_services
from ._discovery import DiscoveryPlugin
from ._host_labels import analyse_cluster_labels, discover_host_labels, HostLabel, HostLabelPlugin
from ._impl import execute_check_discovery
from ._params import DiscoveryCheckParameters
from ._services import analyse_services, discover_services, find_plugins
from ._utils import DiscoveryMode, QualifiedDiscovery

__all__ = [
    "analyse_cluster_labels",
    "analyse_services",
    "AutocheckServiceWithNodes",
    "AutocheckEntry",
    "AutochecksManager",
    "AutochecksStore",
    "autodiscovery",
    "automation_discovery",
    "discover_host_labels",
    "discover_services",
    "DiscoveryCheckParameters",
    "DiscoveryMode",
    "DiscoveryResult",
    "DiscoveryPlugin",
    "execute_check_discovery",
    "find_plugins",
    "get_host_services",
    "HostLabel",
    "HostLabelPlugin",
    "QualifiedDiscovery",
    "remove_autochecks_of_host",
    "set_autochecks_of_cluster",
    "set_autochecks_of_real_hosts",
]
