#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import abc
import socket
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Literal

from cmk import trace
from cmk.base.config import ConfigCache, CoreObjectsConfig
from cmk.ccc.config_path import ConfigCreationContext
from cmk.ccc.hostaddress import HostAddress, HostName, Hosts
from cmk.checkengine.checkerplugin import ConfiguredService
from cmk.checkengine.plugins import AgentBasedPlugins, ServiceID
from cmk.core_client import CoreClient
from cmk.licensing.handler import LicensingHandler
from cmk.password_store.v1 import Secret
from cmk.ruleset_matcher.labels import Labels
from cmk.ruleset_matcher.tags import HostTags
from cmk.utils import ip_lookup
from cmk.utils.servicename import ServiceName

tracer = trace.get_tracer()


@dataclass(frozen=True, kw_only=True, eq=False)
class MonitoringConfigRequest:
    """Everything a monitoring core needs to create its configuration.

    NOTE: This is where the engine puts pre-computed information. Today the cores
    still do most of the computing themselves; every computation that moves out of
    a core should arrive here as a new field.
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


class MonitoringCore(abc.ABC):
    def __init__(self, core_client: CoreClient) -> None:
        self.core_client: Final = core_client

    @classmethod
    @abc.abstractmethod
    def name(cls) -> Literal["nagios", "cmc"]:
        raise NotImplementedError

    @abc.abstractmethod
    def create_monitoring_config(self, request: MonitoringConfigRequest) -> None:
        raise NotImplementedError
