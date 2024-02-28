#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

import cmk.utils.config_warnings as config_warnings
import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.base import plugin_contexts

from cmk.discover_plugins import discover_executable, family_libexec_dir, PluginLocation
from cmk.server_side_calls.v1 import ActiveCheckConfig, HostConfig, HTTPProxy

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
    argument_function: Callable[[Mapping[str, object]], Sequence[str]] | None = None
    service_description: Callable[[Mapping[str, object]], str] | None = None
    service_generator: Callable[
        [HostAddressConfiguration, Mapping[str, object]], Iterator[tuple[str, str]]
    ] | None = None


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


@dataclass(frozen=True)
class ActiveServiceData:
    plugin_name: str
    description: ServiceName
    command: str
    command_display: str
    command_line: str
    params: Mapping[str, object]
    expanded_args: str


@dataclass(frozen=True)
class ActiveServiceDescription:
    plugin_name: str
    description: ServiceName
    params: Mapping[str, object]


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
        self.escape_func = escape_func
        self._use_new_descriptions_for = use_new_descriptions_for

    def get_active_service_data(
        self, active_checks_rules: Sequence[tuple[str, Sequence[Mapping[str, object]]]]
    ) -> Iterator[ActiveServiceData]:
        # remove setting the host context when deleting the old API
        # the host name is passed as an argument in the new API
        with plugin_contexts.current_host(self.host_name):
            for plugin_name, plugin_params in active_checks_rules:
                service_iterator = self._get_service_iterator(plugin_name, plugin_params)

                if not service_iterator:
                    continue

                try:
                    yield from self._get_service_data(plugin_name, service_iterator)
                except InvalidPluginInfoError:
                    config_warnings.warn(
                        f"Invalid configuration (active check: {plugin_name}) on host {self.host_name}: "
                        f"active check plugin is missing an argument function or a service description"
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
        plugin_params: Sequence[Mapping[str, object]],
    ) -> Iterator[tuple[str, str, str, Mapping[str, object]]] | None:
        if (plugin_info_dict := self._legacy_plugins.get(plugin_name)) is not None:
            plugin_info = PluginInfo(
                command_line=plugin_info_dict["command_line"],
                argument_function=plugin_info_dict.get("argument_function"),
                service_description=plugin_info_dict.get("service_description"),
                service_generator=plugin_info_dict.get("service_generator"),
            )
            return self._iterate_legacy_services(plugin_name, plugin_info, plugin_params)

        if (active_check := self._plugins.get(plugin_name)) is not None:
            return self._iterate_services(active_check, plugin_params)

        return None

    def _iterate_services(
        self, active_check: ActiveCheckConfig, plugin_params: Sequence[Mapping[str, object]]
    ) -> Iterator[tuple[str, str, str, Mapping[str, object]]]:
        http_proxies = {
            id: HTTPProxy(id=id, name=proxy["title"], url=proxy["proxy_url"])
            for id, proxy in self._http_proxies.items()
        }

        for param_dict in plugin_params:
            for service in active_check(param_dict, self.host_config, http_proxies):
                arguments = replace_passwords(
                    self.host_name,
                    self.stored_passwords,
                    service.command_arguments,
                )
                command_line = f"check_{active_check.name} {arguments}"
                yield service.service_description, arguments, command_line, param_dict

    def _iterate_legacy_services(
        self,
        plugin_name: str,
        plugin_info: PluginInfo,
        plugin_params: Sequence[Mapping[str, object]],
    ) -> Iterator[tuple[str, str, str, Mapping[str, object]]]:
        for params in plugin_params:
            for desc, args in self._iter_active_check_services(plugin_name, plugin_info, params):
                args_without_macros = replace_macros(args, self.host_config.macros)
                command_line = plugin_info.command_line.replace("$ARG1$", args_without_macros)
                yield desc, args_without_macros, command_line, params

    def _get_service_data(
        self,
        plugin_name: str,
        service_iterator: Iterator[tuple[str, str, str, Mapping[str, object]]],
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

            command, exec_command_line = self._get_command(plugin_name, command_line)

            yield ActiveServiceData(
                plugin_name=plugin_name,
                description=description,
                command=command,
                command_display=f"{command}!{self.escape_func(args)}",
                command_line=exec_command_line,
                params=params,
                expanded_args=self.escape_func(args),
            )

    def _get_command(self, plugin_name: str, command_line: str) -> tuple[str, str]:
        if self.host_attrs["address"] in ["0.0.0.0", "::"]:
            command = "check-mk-custom"
            command_line = 'echo "CRIT - Failed to lookup IP address and no explicit IP address configured"; exit 2'

            return command, command_line

        command = f"check_mk_active-{plugin_name}"
        return command, _autodetect_plugin(
            command_line, self._modules.get(plugin_name.removeprefix("check_"))
        )

    @staticmethod
    def _old_active_http_check_service_description(params: Mapping[str, object]) -> str:
        name = str(params["name"])
        return name[1:] if name.startswith("^") else "HTTP %s" % name

    def _active_check_service_description(
        self,
        plugin_name: str,
        plugin_info: PluginInfo,
        params: Mapping[str, object],
    ) -> ServiceName:
        if not plugin_info.service_description:
            raise InvalidPluginInfoError

        if plugin_name == "http" and plugin_name not in self._use_new_descriptions_for:
            description_with_macros = self._old_active_http_check_service_description(params)
        else:
            description_with_macros = plugin_info.service_description(params)

        description = description_with_macros.replace("$HOSTNAME$", self.host_name).replace(
            "$HOSTALIAS$", self.host_alias
        )

        return self._service_name_finalizer(description)

    def _iter_active_check_services(
        self,
        plugin_name: str,
        plugin_info: PluginInfo,
        params: Mapping[str, object],
    ) -> Iterator[tuple[str, str]]:
        if plugin_info.service_generator:
            host_config = _get_host_address_config(self.host_name, self.host_attrs)

            for desc, args in plugin_info.service_generator(host_config, params):
                yield str(desc), str(args)
            return

        description = self._active_check_service_description(plugin_name, plugin_info, params)

        if not plugin_info.argument_function:
            raise InvalidPluginInfoError

        arguments = commandline_arguments(
            self.host_name,
            description,
            plugin_info.argument_function(params),
            self.stored_passwords,
        )
        yield description, arguments

    def get_active_service_descriptions(
        self, active_checks_rules: Sequence[tuple[str, Sequence[Mapping[str, object]]]]
    ) -> Iterator[ActiveServiceDescription]:
        # remove setting the host context when deleting the old API
        # the host name is passed as an argument in the new API
        with plugin_contexts.current_host(self.host_name):
            for plugin_name, plugin_params in active_checks_rules:
                service_iterator = self._get_service_description_iterator(
                    plugin_name, plugin_params
                )

                if not service_iterator:
                    continue

                try:
                    yield from service_iterator
                except InvalidPluginInfoError:
                    config_warnings.warn(
                        f"Invalid configuration (active check: {plugin_name}) on host {self.host_name}: "
                        f"active check plugin is missing an argument function or a service description"
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
        plugin_params: Sequence[Mapping[str, object]],
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

        if (active_check := self._plugins.get(plugin_name)) is not None:
            return self._iterate_service_descriptions(active_check, plugin_params)

        return None

    def _iterate_legacy_service_descriptions(
        self,
        plugin_name: str,
        plugin_info: PluginInfo,
        plugin_params: Sequence[Mapping[str, object]],
    ) -> Iterator[ActiveServiceDescription]:
        for params in plugin_params:
            if plugin_info.service_generator:
                host_config = _get_host_address_config(self.host_name, self.host_attrs)

                for description, _ in plugin_info.service_generator(host_config, params):
                    yield ActiveServiceDescription(plugin_name, str(description), params)
                return

            description = self._active_check_service_description(plugin_name, plugin_info, params)
            yield ActiveServiceDescription(plugin_name, str(description), params)

    def _iterate_service_descriptions(
        self, active_check: ActiveCheckConfig, plugin_params: Sequence[Mapping[str, object]]
    ) -> Iterator[ActiveServiceDescription]:
        for desc, _args, _command_line, params in self._iterate_services(
            active_check, plugin_params
        ):
            yield ActiveServiceDescription(active_check.name, desc, params)


def _autodetect_plugin(command_line: str, module_name: str | None, *fallbacks: Path) -> str:
    # This condition can only be true in the legacy case.
    # Remove it when possible!
    if command_line[0] in ["$", "/"]:
        return command_line

    libexec_paths = (family_libexec_dir(module_name),) if module_name else ()
    nagios_paths = (
        cmk.utils.paths.local_lib_dir / "nagios/plugins",
        Path(cmk.utils.paths.lib_dir, "nagios/plugins"),
    )
    # When the above case is gone, we can probably pull this
    # function up the callstack and won't have to to do this
    # join - split - rejoin dance.
    plugin_name, *args = command_line.split(None, 1)
    if (full_path := discover_executable(plugin_name, *libexec_paths, *nagios_paths)) is None:
        return command_line

    return " ".join((str(full_path), *args))
