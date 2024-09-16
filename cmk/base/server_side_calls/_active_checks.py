#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Iterator, Mapping, Reversible, Sequence
from dataclasses import dataclass
from pathlib import Path

import cmk.ccc.debug

import cmk.utils.paths
from cmk.utils import config_warnings, password_store
from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.discover_plugins import discover_executable, family_libexec_dir, PluginLocation
from cmk.server_side_calls.v1 import ActiveCheckCommand, ActiveCheckConfig, HostConfig
from cmk.server_side_calls_backend.config_processing import (
    process_configuration_to_parameters,
    ProxyConfig,
)

from ._commons import ConfigSet, replace_passwords, SSCRules


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
        host_attrs: Mapping[str, str],
        http_proxies: Mapping[str, Mapping[str, str]],
        service_name_finalizer: Callable[[ServiceName], ServiceName],
        stored_passwords: Mapping[str, str],
        password_store_file: Path,
    ):
        self._plugins = {p.name: p for p in plugins.values()}
        self._modules = {p.name: l.module for l, p in plugins.items()}
        self.host_name = host_name
        self.host_config = host_config
        self.host_alias = host_attrs["alias"]
        self.host_attrs = host_attrs
        self._http_proxies = http_proxies
        self._service_name_finalizer = service_name_finalizer
        self.stored_passwords = stored_passwords or {}
        self.password_store_file = password_store_file

    def get_active_service_data(
        self, active_checks_rules: Iterable[SSCRules]
    ) -> Iterator[ActiveServiceData]:
        for plugin_name, plugin_params in active_checks_rules:
            try:
                services = self._make_services(plugin_name, plugin_params)
            except Exception as e:
                if cmk.ccc.debug.enabled():
                    raise
                config_warnings.warn(
                    f"Config creation for active check {plugin_name} failed on {self.host_name}: {e}"
                )
                continue

            yield from self._deduplicate_service_descriptions(
                self._drop_empty_service_descriptions(services)
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
        if self.host_attrs["address"] in ["0.0.0.0", "::"]:
            # these 'magic' addresses indicate that the lookup failed :-(
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

        detected_executable = _autodetect_plugin(executable, self._modules.get(active_check.name))

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


def _autodetect_plugin(command: str, module_name: str | None) -> str:
    libexec_paths = (family_libexec_dir(module_name),) if module_name else ()
    nagios_paths = (
        cmk.utils.paths.local_lib_dir / "nagios/plugins",
        Path(cmk.utils.paths.lib_dir, "nagios/plugins"),
    )
    if (full_path := discover_executable(command, *libexec_paths, *nagios_paths)) is None:
        return command

    return str(full_path)
