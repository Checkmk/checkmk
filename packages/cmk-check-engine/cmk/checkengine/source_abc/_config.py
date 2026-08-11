#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Final, Literal

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.fetchers.ipmi import IPMICredentials
from cmk.checkengine.fetchers.snmp import SNMPFetcherConfig, SNMPSectionMeta
from cmk.checkengine.fetchers.tcp import TCPFetcherConfig
from cmk.checkengine.helper_interface import SourceType
from cmk.checkengine.plugin_backend import sections_needing_redetection
from cmk.checkengine.plugins import AgentBasedPlugins, make_plugin_store
from cmk.checkengine.snmplib import SNMPHostConfig, SNMPPluginStore, SNMPSectionName

__all__ = ["SourceConfig"]

_AddressFamily = Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]


class SourceConfig:
    """Configuration and callbacks a host's data sources need to build fetchers.

    This is the seam between the check engine and the (base) configuration: the
    check engine must not read the configuration directly, so every
    configuration-derived value is injected here as a callback.  ``SourceConfig``
    is deliberately agnostic of the concrete ``Fetcher`` and ``Source`` classes -
    it only provides configuration *data*.  The individual sources turn that data
    into their own fetchers.
    """

    def __init__(
        self,
        *,
        snmp_config: Callable[[HostName, _AddressFamily, HostAddress, SourceType], SNMPHostConfig],
        checking_sections: Callable[[AgentBasedPlugins, HostName], frozenset[SNMPSectionName]],
        snmp_exclude_sections: Callable[[HostName], Sequence[Mapping[str, Sequence[str]]]],
        status_data_inventory: Callable[[HostName], bool],
        management_credentials: Callable[[HostName], IPMICredentials],
        program_commandline: Callable[[HostName, _AddressFamily, HostAddress | None, str], str],
        snmp_fetcher_config: SNMPFetcherConfig,
        tcp_fetcher_config: TCPFetcherConfig,
        is_cmc: bool,
        uuid_lookup_dir: Path,
    ) -> None:
        # Pure pass-through callbacks are exposed directly as attributes.
        self.snmp_config: Final = snmp_config
        self.snmp_status_data_inventory: Final = status_data_inventory
        self.program_commandline: Final = program_commandline
        self._checking_sections: Final = checking_sections
        self._snmp_exclude_sections: Final = snmp_exclude_sections
        self._management_credentials: Final = management_credentials
        self.snmp_fetcher_config: Final = snmp_fetcher_config
        self.tcp_fetcher_config: Final = tcp_fetcher_config
        self.is_cmc: Final = is_cmc
        self.uuid_lookup_dir: Final = uuid_lookup_dir

    # .-- SNMP -----------------------------------------------------------------.

    # TODO: `plugins` is constant for a SourceConfig instance and is only passed to
    # the SNMP methods to keep the introducing change small.  It could instead be a
    # constructor argument, so the sources no longer need to hold and forward it.
    def snmp_sections(
        self, plugins: AgentBasedPlugins, host_name: HostName
    ) -> Mapping[SNMPSectionName, SNMPSectionMeta]:
        checking_sections = self._checking_sections(plugins, host_name)
        disabled_sections = self._disabled_snmp_sections(host_name)
        redetect_sections = {
            SNMPSectionName(name)
            for name in sections_needing_redetection(plugins.snmp_sections.values())
        }
        return {
            SNMPSectionName(name): SNMPSectionMeta(
                checking=name in checking_sections,
                disabled=name in disabled_sections,
                redetect=name in checking_sections and name in redetect_sections,
            )
            for name in (checking_sections | disabled_sections)
        }

    def snmp_plugin_store(self, plugins: AgentBasedPlugins) -> SNMPPluginStore:
        return make_plugin_store(plugins)

    def _disabled_snmp_sections(self, host_name: HostName) -> frozenset[SNMPSectionName]:
        """Return the set of disabled SNMP sections."""
        rules = self._snmp_exclude_sections(host_name)
        merged_section_settings = {"if64adm": True}
        for rule in reversed(rules):
            for section in rule.get("sections_enabled", ()):
                merged_section_settings[section] = False
            for section in rule.get("sections_disabled", ()):
                merged_section_settings[section] = True

        return frozenset(
            SNMPSectionName(name)
            for name, is_disabled in merged_section_settings.items()
            if is_disabled
        )

    # '-------------------------------------------------------------------------'

    def ipmi_credentials(self, host_name: HostName) -> tuple[str | None, str | None]:
        credentials = self._management_credentials(host_name)
        return credentials.get("username"), credentials.get("password")
