#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Callable, Iterable, Mapping, Reversible, Sequence
from dataclasses import dataclass

from cmk.ccc.hostaddress import HostName
from cmk.discover_plugins import PluginLocation
from cmk.server_side_calls import internal, v1
from cmk.utils import config_warnings, password_store
from cmk.utils.servicename import ServiceName

from ._commons import ConfigSet, ExecutableFinderProtocol, replace_passwords, SecretsConfig
from ._relay_compatibility import NotSupportedError
from .config_processing import (
    GlobalProxiesWithLookup,
    OAuth2Connection,
    process_configuration_to_parameters,
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
        plugins: Mapping[PluginLocation, internal.ActiveCheckConfig | v1.ActiveCheckConfig],
        host_name: HostName,
        host_config: v1.HostConfig,
        global_proxies_with_lookup: GlobalProxiesWithLookup,
        oauth2_connections: Mapping[str, OAuth2Connection],
        service_name_finalizer: Callable[[ServiceName], ServiceName],
        secrets_config: SecretsConfig,
        finder: ExecutableFinderProtocol,
        *,
        ip_lookup_failed: bool,
        for_relay: bool,
    ):
        self._plugins = {p.name: p for p in plugins.values()}
        self._modules = {p.name: l.module for l, p in plugins.items()}
        self.host_name = host_name
        self.host_config = host_config
        self._global_proxies_with_lookup = global_proxies_with_lookup
        self._oauth2_connections = oauth2_connections
        self._service_name_finalizer = service_name_finalizer
        self._secrets_config = secrets_config
        self._finder = finder
        self._ip_lookup_failed = ip_lookup_failed
        self._for_relay = for_relay

    def get_active_service_data(
        self, plugin_name: str, plugin_params: Iterable[ConfigSet]
    ) -> Sequence[ActiveServiceData]:
        active_services_data = self._deduplicate_service_descriptions(
            self._drop_empty_service_descriptions(self._make_services(plugin_name, plugin_params))
        )

        if (
            active_services_data
            and self._for_relay
            and not self._is_supported_for_relay(plugin_name)
        ):
            # note: more context is given where this exception is handled.
            raise NotSupportedError("This active check is not supported on relays.")

        return active_services_data

    def _is_supported_for_relay(self, plugin_name: str) -> bool:
        # This will depend on the plugin family in the future.
        # The case of our inventory active check is special: It will contact the relay when run on the site.
        return plugin_name == "cmk_inv"

    def _make_services(
        self, plugin_name: str, plugin_params: Iterable[ConfigSet]
    ) -> Sequence[ActiveServiceData]:
        if (active_check := self._plugins.get(plugin_name)) is None:
            return ()

        original_and_processed_configs = (
            (
                config_set,
                process_configuration_to_parameters(
                    config_set,
                    self._global_proxies_with_lookup,
                    self._oauth2_connections,
                    usage_hint=f"plugin: {plugin_name}",
                    is_internal=isinstance(active_check, internal.ActiveCheckConfig),
                ),
            )
            for config_set in plugin_params
        )

        return [
            self._make_service(active_check, service, config_set, params.surrogates)
            for config_set, params in original_and_processed_configs
            for service in active_check(params.value, self.host_config)
        ]

    def _make_service(
        self,
        active_check: v1.ActiveCheckConfig | internal.ActiveCheckConfig,
        service: v1.ActiveCheckCommand,
        conf_dict: Mapping[str, object],
        surrogates: Mapping[int, str],
    ) -> ActiveServiceData:
        if self._ip_lookup_failed:
            executable = "check_always_crit"
            arguments: tuple[str, ...] = (
                "'Failed to lookup IP address and no explicit IP address configured'",
            )
        else:
            executable = f"check_{active_check.name}"
            arguments = replace_passwords(
                self.host_name,
                service.command_arguments,
                self._secrets_config,
                surrogates,
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
