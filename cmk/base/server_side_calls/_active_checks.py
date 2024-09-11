#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

import cmk.ccc.debug

import cmk.utils.paths
from cmk.utils import config_warnings, password_store
from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.discover_plugins import discover_executable, family_libexec_dir, PluginLocation
from cmk.server_side_calls.v1 import ActiveCheckConfig, HostConfig
from cmk.server_side_calls_backend.config_processing import (
    process_configuration_to_parameters,
    ProxyConfig,
)

from ._commons import ConfigSet, replace_passwords, SSCRules


# This class can probably be consolidated to have fewer fields.
# But it's close to the release and I don't dare to touch it.
@dataclass(frozen=True)
class ActiveServiceData:
    plugin_name: str
    description: ServiceName
    command_name: str
    command_display: str
    command_line: str
    params: object
    expanded_args: str
    detected_executable: str


@dataclass(frozen=True)
class ActiveServiceDescription:
    plugin_name: str
    description: ServiceName
    params: Mapping[str, object] | object


# yet another collection of description / command / arguments
# see if we can conslidate these.
@dataclass(frozen=True)
class _RawActiveServiceData:
    plugin_name: str
    description: str
    arguments: str
    configuration: Mapping[str, object]


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
        escape_func: Callable[[str], str] = lambda a: a.replace("!", "\\!"),
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
        self.escape_func = escape_func

    def get_active_service_data(
        self, active_checks_rules: Iterable[SSCRules]
    ) -> Iterator[ActiveServiceData]:
        for plugin_name, plugin_params in active_checks_rules:
            service_iterator = self._iterate_services(plugin_name, plugin_params)

            try:
                yield from self._get_service_data(plugin_name, service_iterator)
            except Exception as e:
                if cmk.ccc.debug.enabled():
                    raise
                config_warnings.warn(
                    f"Config creation for active check {plugin_name} failed on {self.host_name}: {e}"
                )

    def _iterate_services(
        self, plugin_name: str, plugin_params: Iterable[ConfigSet]
    ) -> Iterator[_RawActiveServiceData]:
        if (active_check := self._plugins.get(plugin_name)) is None:
            return
        for conf_dict in plugin_params:
            # actually these ^- are configuration sets.
            proxy_config = ProxyConfig(self.host_name, self._http_proxies)
            processed = process_configuration_to_parameters(conf_dict, proxy_config)

            for service in active_check(processed.value, self.host_config):
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
                yield _RawActiveServiceData(
                    plugin_name=active_check.name,
                    description=service.service_description,
                    arguments=arguments,
                    configuration=conf_dict,
                )

    def _get_service_data(
        self,
        plugin_name: str,
        service_iterator: Iterator[_RawActiveServiceData],
    ) -> Iterator[ActiveServiceData]:
        existing_descriptions: dict[str, str] = {}

        for raw_service in service_iterator:
            if not raw_service.description:
                config_warnings.warn(
                    f"Skipping invalid service with empty description "
                    f"(active check: {raw_service.plugin_name}) on host {self.host_name}"
                )
                continue

            if raw_service.description in existing_descriptions:
                # If we have the same active check again with the same description,
                # then we do not regard this as an error, but simply ignore the
                # second one. That way one can override a check with other settings.
                continue

            existing_descriptions[raw_service.description] = raw_service.plugin_name

            command, detected_executable, args = self._get_command(raw_service)

            yield ActiveServiceData(
                plugin_name=plugin_name,
                description=raw_service.description,
                command_name=command,
                command_display=f"{command}!{self.escape_func(args)}",
                command_line=f"{detected_executable} {args}".rstrip(),
                params=raw_service.configuration,
                expanded_args=self.escape_func(args),
                detected_executable=detected_executable,
            )

    def _get_command(self, raw_service: _RawActiveServiceData) -> tuple[str, str, str]:
        if self.host_attrs["address"] in ["0.0.0.0", "::"]:
            # these 'magic' addresses indicate that the lookup failed :-(
            executable = "check_always_crit"
            args = "'Failed to lookup IP address and no explicit IP address configured'"

        else:
            executable = f"check_{raw_service.plugin_name}"
            args = raw_service.arguments

        command = f"check_mk_active-{raw_service.plugin_name}"
        detected_executable = _autodetect_plugin(
            executable, self._modules.get(raw_service.plugin_name)
        )
        return (command, detected_executable, args)

    def get_active_service_descriptions(
        self, active_checks_rules: Iterable[SSCRules]
    ) -> Iterator[ActiveServiceDescription]:
        for plugin_name, plugin_params in active_checks_rules:
            try:
                for raw_service in self._iterate_services(plugin_name, plugin_params):
                    yield ActiveServiceDescription(
                        plugin_name, raw_service.description, raw_service.configuration
                    )
            except Exception as e:
                if cmk.ccc.debug.enabled():
                    raise
                config_warnings.warn(
                    f"Config creation for active check {plugin_name} failed on {self.host_name}: {e}"
                )


def _autodetect_plugin(command: str, module_name: str | None) -> str:
    libexec_paths = (family_libexec_dir(module_name),) if module_name else ()
    nagios_paths = (
        cmk.utils.paths.local_lib_dir / "nagios/plugins",
        Path(cmk.utils.paths.lib_dir, "nagios/plugins"),
    )
    if (full_path := discover_executable(command, *libexec_paths, *nagios_paths)) is None:
        return command

    return str(full_path)
