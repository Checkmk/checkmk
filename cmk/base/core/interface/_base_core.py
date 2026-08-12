#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import abc
import socket
from collections.abc import Callable, Mapping, Sequence
from typing import Final, Literal

from cmk import trace
from cmk.base.config import ConfigCache, CoreObjectsConfig
from cmk.ccc.config_path import ConfigCreationContext
from cmk.ccc.hostaddress import HostAddress, HostName, Hosts
from cmk.checkengine.checkerplugin import ConfiguredService
from cmk.checkengine.plugins import AgentBasedPlugins, ServiceID
from cmk.core_client import CoreClient
from cmk.licensing.basics.paths import get_licensed_state_file_path
from cmk.licensing.handler import LicensingHandler
from cmk.password_store.v1_unstable import Secret
from cmk.ruleset_matcher.labels import Labels
from cmk.ruleset_matcher.tags import HostTags
from cmk.utils import ip_lookup, paths
from cmk.utils.servicename import ServiceName

tracer = trace.get_tracer()


class MonitoringCore(abc.ABC):
    def __init__(
        self, core_client: CoreClient, licensing_handler_factory: Callable[[], LicensingHandler]
    ):
        self.licensing_handler_factory: Final = licensing_handler_factory
        self.core_client: Final = core_client

    @classmethod
    @abc.abstractmethod
    def name(cls) -> Literal["nagios", "cmc"]:
        raise NotImplementedError

    def create_config(
        self,
        config_creation_context: ConfigCreationContext,
        config_cache: ConfigCache,
        core_objects_config: CoreObjectsConfig,
        hosts_config: Hosts,
        host_tags: HostTags,
        final_service_name_config: Callable[
            [HostName, ServiceName, Callable[[HostName], Labels]], ServiceName
        ],
        passive_service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
        enforced_services_table: Callable[
            [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
        ],
        plugins: AgentBasedPlugins,
        get_ip_stack_config: Callable[[HostName], ip_lookup.IPStackConfig],
        default_address_family: Callable[
            [HostName], Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]
        ],
        ip_address_of: ip_lookup.ConfiguredIPLookup[ip_lookup.CollectFailedHosts],
        ip_address_of_mgmt: ip_lookup.IPLookupOptional,
        passwords: Mapping[str, Secret[str]],
        hosts_to_update: set[HostName] | None,
        service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]],
    ) -> None:
        licensing_handler = self.licensing_handler_factory()
        licensing_handler.persist_licensed_state(get_licensed_state_file_path(paths.omd_root))
        self._create_config(
            config_creation_context,
            config_cache,
            core_objects_config,
            hosts_config,
            host_tags,
            final_service_name_config,
            passive_service_name_config,
            enforced_services_table,
            get_ip_stack_config,
            default_address_family,
            ip_address_of,
            ip_address_of_mgmt,
            licensing_handler,
            plugins,
            passwords,
            hosts_to_update=hosts_to_update,
            service_depends_on=service_depends_on,
        )

    @abc.abstractmethod
    def _create_config(
        self,
        config_creation_context: ConfigCreationContext,
        config_cache: ConfigCache,
        core_objects_config: CoreObjectsConfig,
        hosts_config: Hosts,
        host_tags: HostTags,
        final_service_name_config: Callable[
            [HostName, ServiceName, Callable[[HostName], Labels]], ServiceName
        ],
        passive_service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
        enforced_services_table: Callable[
            [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
        ],
        get_ip_stack_config: Callable[[HostName], ip_lookup.IPStackConfig],
        default_address_family: Callable[
            [HostName], Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]
        ],
        ip_address_of: ip_lookup.ConfiguredIPLookup[ip_lookup.CollectFailedHosts],
        ip_address_of_mgmt: ip_lookup.IPLookupOptional,
        licensing_handler: LicensingHandler,
        plugins: AgentBasedPlugins,
        passwords: Mapping[str, Secret[str]],
        *,
        hosts_to_update: set[HostName] | None = None,
        service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]],
    ) -> None:
        raise NotImplementedError
