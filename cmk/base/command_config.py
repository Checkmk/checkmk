#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

import cmk.utils.config_warnings as config_warnings
from cmk.utils.hostaddress import HostName
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher
from cmk.utils.servicename import ServiceName

import cmk.base.config as base_config
import cmk.base.core_config as core_config
from cmk.base.api.agent_based import plugin_contexts


class InvalidPluginInfoError(Exception):
    pass


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
    hostname: str, host_attrs: Mapping[str, str]
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
        hostname=hostname,
        host_address=host_attrs["address"],
        alias=host_attrs["alias"],
        ipv4address=host_attrs.get("_ADDRESS_4"),
        ipv6address=host_attrs.get("_ADDRESS_6"),
        indexed_ipv4addresses=dict(_get_indexed_addresses(host_attrs, "4")),
        indexed_ipv6addresses=dict(_get_indexed_addresses(host_attrs, "6")),
    )


class ActiveCheckConfig:
    def __init__(
        self,
        host_name: HostName,
        host_attrs: Mapping[str, str],
        macros: Mapping[str, str] | None = None,
        stored_passwords: Mapping[str, str] | None = None,
        escape_func: Callable[[str], str] = lambda a: a.replace("!", "\\!"),
    ):
        self.host_name = host_name
        self.host_alias = host_attrs["alias"]
        self.host_attrs = host_attrs
        self.macros = macros or {}
        self.stored_passwords = stored_passwords or {}
        self.escape_func = escape_func

    def get_active_service_data(
        self,
        matcher: RulesetMatcher,
        active_checks: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    ) -> Iterator[ActiveServiceData]:
        # remove setting the host context when deleting the old API
        # the host name is passed as an argument in the new API
        with plugin_contexts.current_host(self.host_name):
            for plugin_name, plugin_params in active_checks:
                if (plugin_info_dict := base_config.active_check_info.get(plugin_name)) is not None:
                    plugin_info = PluginInfo(
                        command_line=plugin_info_dict["command_line"],
                        argument_function=plugin_info_dict.get("argument_function"),
                        service_description=plugin_info_dict.get("service_description"),
                        service_generator=plugin_info_dict.get("service_generator"),
                    )
                    try:
                        yield from self._get_legacy_service_data(
                            matcher, plugin_name, plugin_params, plugin_info
                        )
                    except InvalidPluginInfoError:
                        config_warnings.warn(
                            f"Invalid configuration (active check: {plugin_name}) on host {self.host_name}: "
                            f"active check plugin is missing an argument function or a service description"
                        )
                        continue

    def _get_legacy_service_data(
        self,
        matcher: RulesetMatcher,
        plugin_name: str,
        plugin_params: Sequence[Mapping[str, object]],
        plugin_info: PluginInfo,
    ) -> Iterator[ActiveServiceData]:
        existing_descriptions: dict[str, str] = {}

        for params in plugin_params:
            for description, args in self._iter_active_check_services(
                matcher, plugin_name, plugin_info, params
            ):
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

                command, command_line = self._get_command(plugin_name, plugin_info, args)

                yield ActiveServiceData(
                    plugin_name=plugin_name,
                    description=description,
                    command=command,
                    command_display=f"{command}!{self.escape_func(args)}",
                    command_line=command_line,
                    params=params,
                    expanded_args=self.escape_func(self._replace_macros(args)),
                )

    def _get_command(
        self, plugin_name: str, plugin_info: PluginInfo, service_args: str
    ) -> tuple[str, str]:
        if self.host_attrs["address"] in ["0.0.0.0", "::"]:
            command = "check-mk-custom"
            command_line = 'echo "CRIT - Failed to lookup IP address and no explicit IP address configured"; exit 2'

            return command, command_line

        command = f"check_mk_active-{plugin_name}"
        command_line_without_macros = self._replace_macros(
            plugin_info.command_line.replace("$ARG1$", service_args)
        )
        return command, core_config.autodetect_plugin(command_line_without_macros)

    def _replace_macros(self, string: str) -> str:
        for macro, replacement in self.macros.items():
            string = string.replace(macro, str(replacement))
        return string

    @staticmethod
    def _old_active_http_check_service_description(params: Mapping[str, object]) -> str:
        name = str(params["name"])
        return name[1:] if name.startswith("^") else "HTTP %s" % name

    def _active_check_service_description(
        self,
        matcher: RulesetMatcher,
        plugin_name: str,
        plugin_info: PluginInfo,
        params: Mapping[str, object],
    ) -> ServiceName:
        if not plugin_info.service_description:
            raise InvalidPluginInfoError

        if plugin_name == "http" and plugin_name not in base_config.use_new_descriptions_for:
            description_with_macros = self._old_active_http_check_service_description(params)
        else:
            description_with_macros = plugin_info.service_description(params)

        description = description_with_macros.replace("$HOSTNAME$", self.host_name).replace(
            "$HOSTALIAS$", self.host_alias
        )

        return base_config.get_final_service_description(matcher, self.host_name, description)

    def _iter_active_check_services(
        self,
        matcher: RulesetMatcher,
        plugin_name: str,
        plugin_info: PluginInfo,
        params: Mapping[str, object],
    ) -> Iterator[tuple[str, str]]:
        if plugin_info.service_generator:
            host_config = _get_host_address_config(self.host_name, self.host_attrs)

            for desc, args in plugin_info.service_generator(host_config, params):
                yield str(desc), str(args)
            return

        description = self._active_check_service_description(
            matcher, plugin_name, plugin_info, params
        )

        if not plugin_info.argument_function:
            raise InvalidPluginInfoError

        arguments = base_config.commandline_arguments(
            self.host_name,
            description,
            plugin_info.argument_function(params),
            self.stored_passwords,
        )
        yield description, arguments

    def get_active_service_descriptions(
        self,
        matcher: RulesetMatcher,
        active_checks: Sequence[tuple[str, Sequence[Mapping[str, object]]]],
    ) -> Iterator[ActiveServiceDescription]:
        # remove setting the host context when deleting the old API
        # the host name is passed as an argument in the new API
        with plugin_contexts.current_host(self.host_name):
            for plugin_name, plugin_params in active_checks:
                if (plugin_info_dict := base_config.active_check_info.get(plugin_name)) is not None:
                    plugin_info = PluginInfo(
                        command_line=plugin_info_dict["command_line"],
                        argument_function=plugin_info_dict.get("argument_function"),
                        service_description=plugin_info_dict.get("service_description"),
                        service_generator=plugin_info_dict.get("service_generator"),
                    )
                    try:
                        yield from self._get_legacy_service_descriptions(
                            matcher, plugin_name, plugin_params, plugin_info
                        )
                    except InvalidPluginInfoError:
                        config_warnings.warn(
                            f"Invalid configuration (active check: {plugin_name}) on host {self.host_name}: "
                            f"active check plugin is missing an argument function or a service description"
                        )
                        continue

    def _get_legacy_service_descriptions(
        self,
        matcher: RulesetMatcher,
        plugin_name: str,
        plugin_params: Sequence[Mapping[str, object]],
        plugin_info: PluginInfo,
    ) -> Iterator[ActiveServiceDescription]:
        for params in plugin_params:
            if plugin_info.service_generator:
                host_config = _get_host_address_config(self.host_name, self.host_attrs)

                for description, _ in plugin_info.service_generator(host_config, params):
                    yield ActiveServiceDescription(plugin_name, str(description), params)
                return

            description = self._active_check_service_description(
                matcher, plugin_name, plugin_info, params
            )
            yield ActiveServiceDescription(plugin_name, str(description), params)
