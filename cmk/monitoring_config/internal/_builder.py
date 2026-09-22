#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import socket
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from cmk.base.config import ConfigCache, CoreObjectsConfig
from cmk.ccc.config_path import ConfigCreationContext
from cmk.ccc.hostaddress import HostAddress, HostName, Hosts
from cmk.checkengine.checkerplugin import ConfiguredService
from cmk.checkengine.plugins import AgentBasedPlugins, ServiceID
from cmk.licensing.handler import LicensingHandler
from cmk.password_store.v1 import Secret
from cmk.ruleset_matcher.labels import Labels
from cmk.ruleset_matcher.tags import HostTags
from cmk.utils import ip_lookup
from cmk.utils.servicename import ServiceName


@dataclass(frozen=True, kw_only=True, eq=False)
class IntermediateMonitoringConfig:
    """The resolved configuration every monitoring config plug-in starts from.

    The engine builds this once per activation. Each plug-in turns it into the
    configuration of its own subsystem -- a monitoring core, the check helpers,
    the relays -- and needs to know nothing about the others.

    Two things it should be, and today is not:

    It should be as simple as it can be, and typed in a self-sufficient way: data
    that means something on its own, without reaching back into `cmk.base`. Today
    it hands out `ConfigCache`, `CoreObjectsConfig` and a fistful of callables, so
    a plug-in reading it still needs half of `cmk.base` to make sense of it.

    It should already hold the expensive answers. Much of what the Microcore
    configuration generation does today is not Microcore-specific: deciding which
    hosts actually changed since the last activation and reusing the rest, walking
    the hosts in parallel, narrowing the ruleset optimizer to the hosts being
    worked on, and assembling the service table -- which the Nagios side then
    assembles a second time, from the same sources in the same order. That work
    belongs here, done once by the engine, so that no core repeats it and every
    plug-in gets it.
    """

    # created by the engine per activation
    config_creation_context: ConfigCreationContext
    passwords: Mapping[str, Secret[str]]
    licensing_handler: LicensingHandler

    # what shall be monitored
    config_cache: ConfigCache
    core_objects_config: CoreObjectsConfig
    hosts_config: Hosts
    host_tags: HostTags
    plugins: AgentBasedPlugins
    hosts_to_update: set[HostName] | None

    # naming / lookups
    final_service_name_config: Callable[
        [HostName, ServiceName, Callable[[HostName], Labels]], ServiceName
    ]
    passive_service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName]
    enforced_services_table: Callable[
        [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
    ]
    get_ip_stack_config: Callable[[HostName], ip_lookup.IPStackConfig]
    default_address_family: Callable[
        [HostName], Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]
    ]
    ip_address_of: ip_lookup.ConfiguredIPLookup[ip_lookup.CollectFailedHosts]
    ip_address_of_mgmt: ip_lookup.IPLookupOptional
    service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]]


@dataclass(frozen=True, kw_only=True, eq=False)
class MonitoringConfigBuilder:
    """Build a subsytems monitoring configuration from the intermediate config"""

    name: str
    build: Callable[[IntermediateMonitoringConfig], None]
