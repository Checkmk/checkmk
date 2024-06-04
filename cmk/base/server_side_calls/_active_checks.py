#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Container, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import cmk.utils.debug
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

from ._commons import commandline_arguments, replace_macros, replace_passwords


class InvalidPluginInfoError(Exception):
    pass


@dataclass(frozen=True)
class HostAddressConfiguration:
    hostname: str
    host_address: str
    alias: str
    ipv4address: str | None
    ipv6address: str | None
    indexed_ipv4addresses: dict[str, str]
    indexed_ipv6addresses: dict[str, str]


@dataclass(frozen=True)
class PluginInfo:
    command_line: str
    argument_function: Callable[[object], Sequence[str]] | None = None
    service_description: Callable[[object], str] | None = None
    service_generator: (
        Callable[[HostAddressConfiguration, object], Iterator[tuple[str, str]]] | None
    ) = None


def _get_host_address_config(
    host_name: str, host_attrs: Mapping[str, str]
) -> HostAddressConfiguration:
    def _get_indexed_addresses(
        host_attrs: Mapping[str, str], address_family: Literal["4", "6"]
    ) -> Iterator[tuple[str, str]]:
        for name, address in host_attrs.items():
            address_template = f"_ADDRESSES_{address_family}_"
            if address_template in name:
                index = name.removeprefix(address_template)
                yield f"$_HOSTADDRESSES_{address_family}_{index}$", address

    return HostAddressConfiguration(
        hostname=host_name,
        host_address=host_attrs["address"],
        alias=host_attrs["alias"],
        ipv4address=host_attrs.get("_ADDRESS_4"),
        ipv6address=host_attrs.get("_ADDRESS_6"),
        indexed_ipv4addresses=dict(_get_indexed_addresses(host_attrs, "4")),
        indexed_ipv6addresses=dict(_get_indexed_addresses(host_attrs, "6")),
    )


# This class can probably be consolidated to have fewer fields.
# But it's close to the release and I don't dare to touch it.
@dataclass(frozen=True)
class ActiveServiceData:
    plugin_name: str
    description: ServiceName
    command: str
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


def _ensure_mapping_str_object(values: Sequence[object]) -> Sequence[Mapping[str, object]]:
    # for the new API, we can be sure that there are only Mappings.
    for value in values:
        if not isinstance(value, dict):
            raise TypeError(value)
    return values  # type: ignore[return-value]


class ActiveCheck:
    def __init__(
        self,
        plugins: Mapping[PluginLocation, ActiveCheckConfig],
        legacy_plugins: Mapping[str, Mapping[str, Any]],
        host_name: HostName,
        host_config: HostConfig,
        host_attrs: Mapping[str, str],
        http_proxies: Mapping[str, Mapping[str, str]],
        service_name_finalizer: Callable[[ServiceName], ServiceName],
        use_new_descriptions_for: Container[str],
        stored_passwords: Mapping[str, str],
        password_store_file: Path,
        escape_func: Callable[[str], str] = lambda a: a.replace("!", "\\!"),
    ):
        self._plugins = {p.name: p for p in plugins.values()}
        self._modules = {p.name: l.module for l, p in plugins.items()}
        self._legacy_plugins = legacy_plugins
        self.host_name = host_name
        self.host_config = host_config
        self.host_alias = host_attrs["alias"]
        self.host_attrs = host_attrs
        self._http_proxies = http_proxies
        self._service_name_finalizer = service_name_finalizer
        self.stored_passwords = stored_passwords or {}
        self.password_store_file = password_store_file
        self.escape_func = escape_func
        self._use_new_descriptions_for = use_new_descriptions_for

    def get_active_service_data(
        self, active_checks_rules: Sequence[tuple[str, Sequence[Mapping[str, object] | object]]]
    ) -> Iterator[ActiveServiceData]:
        # remove setting the host context when deleting the old API
        # the host name is passed as an argument in the new API
        for plugin_name, plugin_params in active_checks_rules:
            service_iterator = self._get_service_iterator(plugin_name, plugin_params)

            if not service_iterator:
                continue

            try:
                yield from self._get_service_data(plugin_name, service_iterator)
            except InvalidPluginInfoError:
                config_warnings.warn(
                    f"Invalid configuration (active check: {plugin_name}) on host {self.host_name}: "
                    f"active check plug-in is missing an argument function or a service description"
                )
            except Exception as e:
                if cmk.utils.debug.enabled():
                    raise
                config_warnings.warn(
                    f"Config creation for active check {plugin_name} failed on {self.host_name}: {e}"
                )

    def _get_service_iterator(
        self,
        plugin_name: str,
        plugin_params: Sequence[Mapping[str, object] | object],
    ) -> Iterator[tuple[str, str, str, object]] | None:
        if (plugin_info_dict := self._legacy_plugins.get(plugin_name)) is not None:
            plugin_info = PluginInfo(
                command_line=plugin_info_dict["command_line"],
                argument_function=plugin_info_dict.get("argument_function"),
                service_description=plugin_info_dict.get("service_description"),
                service_generator=plugin_info_dict.get("service_generator"),
            )
            return self._iterate_legacy_services(plugin_name, plugin_info, plugin_params)

        plugin_params = _ensure_mapping_str_object(plugin_params)
        if (active_check := self._plugins.get(plugin_name)) is not None:
            return self._iterate_services(active_check, plugin_params)

        return None

    def _iterate_services(
        self, active_check: ActiveCheckConfig, plugin_params: Sequence[Mapping[str, object]]
    ) -> Iterator[tuple[str, str, str, Mapping[str, object]]]:
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
                command_line = f"check_{active_check.name} {arguments}"
                yield service.service_description, arguments, command_line, conf_dict

    def _iterate_legacy_services(
        self,
        plugin_name: str,
        plugin_info: PluginInfo,
        plugin_params: Sequence[object],
    ) -> Iterator[tuple[str, str, str, object]]:
        for params in plugin_params:
            for desc, args in self._iter_active_check_services(plugin_name, plugin_info, params):
                args_without_macros = replace_macros(args, self.host_config.macros)
                command_line = plugin_info.command_line.replace("$ARG1$", args_without_macros)
                yield desc, args_without_macros, command_line, params

    def _get_service_data(
        self,
        plugin_name: str,
        service_iterator: Iterator[tuple[str, str, str, object]],
    ) -> Iterator[ActiveServiceData]:
        existing_descriptions: dict[str, str] = {}

        for description, args, command_line, params in service_iterator:
            if not description:
                config_warnings.warn(
                    f"Skipping invalid service with empty description "
                    f"(active check: {plugin_name}) on host {self.host_name}"
                )
                continue

            if description in existing_descriptions:
                # If we have the same active check again with the same description,
                # then we do not regard this as an error, but simply ignore the
                # second one. That way one can override a check with other settings.
                continue

            existing_descriptions[description] = plugin_name

            command, detected_exectutable, exec_command_line = self._get_command(
                plugin_name, command_line
            )

            yield ActiveServiceData(
                plugin_name=plugin_name,
                description=description,
                command=command,
                command_display=f"{command}!{self.escape_func(args)}",
                command_line=exec_command_line,
                params=params,
                expanded_args=self.escape_func(args),
                detected_executable=detected_exectutable,
            )

    def _get_command(self, plugin_name: str, command_line: str) -> tuple[str, str, str]:
        # TODO: check why/if we need this. Couldn't we have for example an active check that
        # queries some RestAPI?
        # This may be a leftover from a time where we would try to replace these in a macro?
        if self.host_attrs["address"] in ["0.0.0.0", "::"]:
            command = "check-mk-custom"
            command_line = 'echo "CRIT - Failed to lookup IP address and no explicit IP address configured"; exit 2'

            return command, "echo", command_line

        command = f"check_mk_active-{plugin_name}"
        executable, *args = command_line.split(None, 1)
        detected_executable = _autodetect_plugin(
            executable, self._modules.get(plugin_name.removeprefix("check_"))
        )
        return command, detected_executable, " ".join((detected_executable, *args))

    def _active_check_service_description(
        self,
        plugin_info: PluginInfo,
        params: object,
    ) -> ServiceName:
        if not plugin_info.service_description:
            raise InvalidPluginInfoError

        description = (
            plugin_info.service_description(params)
            .replace("$HOSTNAME$", self.host_name)
            .replace("$HOSTALIAS$", self.host_alias)
        )

        return self._service_name_finalizer(description)

    def _iter_active_check_services(
        self,
        plugin_name: str,
        plugin_info: PluginInfo,
        params: object,
    ) -> Iterator[tuple[str, str]]:
        if plugin_info.service_generator:
            host_config = _get_host_address_config(self.host_name, self.host_attrs)

            for desc, args in plugin_info.service_generator(host_config, params):
                yield str(desc), str(args)
            return

        description = self._active_check_service_description(plugin_info, params)

        if not plugin_info.argument_function:
            raise InvalidPluginInfoError

        arguments = commandline_arguments(
            self.host_name,
            description,
            plugin_info.argument_function(params),
            self.stored_passwords,
            self.password_store_file,
        )
        yield description, arguments

    def get_active_service_descriptions(
        self, active_checks_rules: Sequence[tuple[str, Sequence[Mapping[str, object] | object]]]
    ) -> Iterator[ActiveServiceDescription]:
        # remove setting the host context when deleting the old API
        # the host name is passed as an argument in the new API
        for plugin_name, plugin_params in active_checks_rules:
            service_iterator = self._get_service_description_iterator(plugin_name, plugin_params)

            if not service_iterator:
                continue

            try:
                yield from service_iterator
            except InvalidPluginInfoError:
                config_warnings.warn(
                    f"Invalid configuration (active check: {plugin_name}) on host {self.host_name}: "
                    f"active check plug-in is missing an argument function or a service description"
                )
                continue
            except Exception as e:
                if cmk.utils.debug.enabled():
                    raise
                config_warnings.warn(
                    f"Config creation for active check {plugin_name} failed on {self.host_name}: {e}"
                )

    def _get_service_description_iterator(
        self,
        plugin_name: str,
        plugin_params: Sequence[Mapping[str, object] | object],
    ) -> Iterator[ActiveServiceDescription] | None:
        if (plugin_info_dict := self._legacy_plugins.get(plugin_name)) is not None:
            plugin_info = PluginInfo(
                command_line=plugin_info_dict["command_line"],
                argument_function=plugin_info_dict.get("argument_function"),
                service_description=plugin_info_dict.get("service_description"),
                service_generator=plugin_info_dict.get("service_generator"),
            )
            return self._iterate_legacy_service_descriptions(
                plugin_name, plugin_info, plugin_params
            )

        plugin_params = _ensure_mapping_str_object(plugin_params)
        if (active_check := self._plugins.get(plugin_name)) is not None:
            return self._iterate_service_descriptions(active_check, plugin_params)

        return None

    def _iterate_legacy_service_descriptions(
        self,
        plugin_name: str,
        plugin_info: PluginInfo,
        plugin_params: Sequence[Mapping[str, object] | object],
    ) -> Iterator[ActiveServiceDescription]:
        for params in plugin_params:
            if plugin_info.service_generator:
                host_config = _get_host_address_config(self.host_name, self.host_attrs)

                for description, _ in plugin_info.service_generator(host_config, params):
                    yield ActiveServiceDescription(plugin_name, str(description), params)
                return

            description = self._active_check_service_description(plugin_info, params)
            yield ActiveServiceDescription(plugin_name, str(description), params)

    def _iterate_service_descriptions(
        self, active_check: ActiveCheckConfig, plugin_params: Sequence[Mapping[str, object]]
    ) -> Iterator[ActiveServiceDescription]:
        for desc, _args, _command_line, params in self._iterate_services(
            active_check, plugin_params
        ):
            yield ActiveServiceDescription(active_check.name, desc, params)


def _autodetect_plugin(command: str, module_name: str | None) -> str:
    # This condition can only be true in the legacy case.
    # Remove it when possible!
    if command.startswith(("$", "/")):
        return command

    libexec_paths = (family_libexec_dir(module_name),) if module_name else ()
    nagios_paths = (
        cmk.utils.paths.local_lib_dir / "nagios/plugins",
        Path(cmk.utils.paths.lib_dir, "nagios/plugins"),
    )
    if (full_path := discover_executable(command, *libexec_paths, *nagios_paths)) is None:
        return command

    return str(full_path)
