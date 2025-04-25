#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, Reversible, Sequence
from dataclasses import dataclass
from pathlib import Path

from cmk.ccc.hostaddress import HostName

from cmk.utils import config_warnings, password_store
from cmk.utils.servicename import ServiceName

from cmk.discover_plugins import PluginLocation
from cmk.server_side_calls.v1 import ActiveCheckCommand, ActiveCheckConfig, HostConfig

from ._commons import ConfigSet, ExecutableFinderProtocol, replace_passwords
from .config_processing import (
    process_configuration_to_parameters,
    ProxyConfig,
)


@dataclass(frozen=True)
class ActiveServiceData:
    plugin_name: str
    configuration: Mapping[str, object]
    description: ServiceName
    command_name: str
    command: tuple[str, ...]


class ActiveCheck:
    def __init__(
        self,
        plugins: Mapping[PluginLocation, ActiveCheckConfig],
        host_name: HostName,
        host_config: HostConfig,
        http_proxies: Mapping[str, Mapping[str, str]],
        service_name_finalizer: Callable[[ServiceName], ServiceName],
        stored_passwords: Mapping[str, str],
        password_store_file: Path,
        finder: ExecutableFinderProtocol,
        *,
        ip_lookup_failed: bool,
    ):
        self._plugins = {p.name: p for p in plugins.values()}
        self._modules = {p.name: l.module for l, p in plugins.items()}
        self.host_name = host_name
        self.host_config = host_config
        self._http_proxies = http_proxies
        self._service_name_finalizer = service_name_finalizer
        self.stored_passwords = stored_passwords or {}
        self.password_store_file = password_store_file
        self._finder = finder
        self._ip_lookup_failed = ip_lookup_failed

    def get_active_service_data(
        self, plugin_name: str, plugin_params: Iterable[ConfigSet]
    ) -> Sequence[ActiveServiceData]:
        return self._deduplicate_service_descriptions(
            self._drop_empty_service_descriptions(self._make_services(plugin_name, plugin_params))
        )

    def _make_services(
        self, plugin_name: str, plugin_params: Iterable[ConfigSet]
    ) -> Sequence[ActiveServiceData]:
        if (active_check := self._plugins.get(plugin_name)) is None:
            return ()

        proxy_config = ProxyConfig(self.host_name, self._http_proxies)
        return [
            self._make_service(active_check, service, proxy_config, configuration_set)
            for configuration_set in plugin_params
            for processed in [process_configuration_to_parameters(configuration_set, proxy_config)]
            for service in active_check(processed.value, self.host_config)
        ]

    def _make_service(
        self,
        active_check: ActiveCheckConfig,
        service: ActiveCheckCommand,
        proxy_config: ProxyConfig,
        conf_dict: Mapping[str, object],
    ) -> ActiveServiceData:
        if self._ip_lookup_failed:
            executable = "check_always_crit"
            arguments: tuple[str, ...] = (
                "'Failed to lookup IP address and no explicit IP address configured'",
            )
        else:
            executable = f"check_{active_check.name}"
            processed = process_configuration_to_parameters(conf_dict, proxy_config)
            arguments = replace_passwords(
                self.host_name,
                service.command_arguments,
                self.stored_passwords,
                self.password_store_file,
                processed.surrogates,
                apply_password_store_hack=password_store.hack.HACK_CHECKS.get(
                    active_check.name, False
                ),
            )

        detected_executable = self._finder(executable, self._modules.get(active_check.name))

        return ActiveServiceData(
            plugin_name=active_check.name,
            configuration=conf_dict,
            description=self._service_name_finalizer(service.service_description),
            command_name=f"check_mk_active-{active_check.name}",
            command=(detected_executable, *arguments),
        )

    def _drop_empty_service_descriptions(
        self,
        services: Iterable[ActiveServiceData],
    ) -> Sequence[ActiveServiceData]:
        # too bad we didn't think of this when we designed the API :-(
        def _keep(service: ActiveServiceData) -> bool:
            if service.description:
                return True
            config_warnings.warn(
                f"Skipping invalid service with empty description "
                f"(active check: {service.plugin_name}) on host {self.host_name}"
            )
            return False

        return [s for s in services if _keep(s)]

    def _deduplicate_service_descriptions(
        self,
        services: Reversible[ActiveServiceData],
    ) -> Sequence[ActiveServiceData]:
        """Drops duplicate service descriptions, keeping the first one.

        If the same active check repeats the same description, we do not
        regard this as an error, but simply ignore the second one.
        That way one can override a check with other settings.
        """
        seen: dict[ServiceName, ActiveServiceData] = {}
        return [seen.setdefault(s.description, s) for s in services if s.description not in seen]
