#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Iterator, Mapping, MutableMapping

import cmk.utils.debug
import cmk.utils.misc
import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException, MKTimeout, OnError
from cmk.utils.hostaddress import HostName
from cmk.utils.log import console

from cmk.checkengine import DiscoveryPlugin, HostKey, plugin_contexts, SourceType
from cmk.checkengine.check_table import ServiceID
from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.discovery import AutocheckEntry
from cmk.checkengine.sectionparser import Provider
from cmk.checkengine.sectionparserutils import get_section_kwargs


def discover_services(
    host_name: HostName,
    plugin_names: Iterable[CheckPluginName],
    *,
    providers: Mapping[HostKey, Provider],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    on_error: OnError,
) -> Iterable[AutocheckEntry]:
    service_table: MutableMapping[ServiceID, AutocheckEntry] = {}
    try:
        with plugin_contexts.current_host(host_name):
            for check_plugin_name in plugin_names:
                try:
                    service_table.update(
                        {
                            entry.id(): entry
                            for entry in _discover_plugins_services(
                                check_plugin_name=check_plugin_name,
                                plugins=plugins,
                                host_key=HostKey(
                                    host_name,
                                    (
                                        SourceType.MANAGEMENT
                                        if check_plugin_name.is_management_name()
                                        else SourceType.HOST
                                    ),
                                ),
                                providers=providers,
                                on_error=on_error,
                            )
                        }
                    )
                except (KeyboardInterrupt, MKTimeout):
                    raise
                except Exception as e:
                    if on_error is OnError.RAISE:
                        raise
                    if on_error is OnError.WARN:
                        console.error(f"Discovery of '{check_plugin_name}' failed: {e}\n")

            return service_table.values()

    except KeyboardInterrupt:
        raise MKGeneralException("Interrupted by Ctrl-C.")


def _discover_plugins_services(
    *,
    check_plugin_name: CheckPluginName,
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    host_key: HostKey,
    providers: Mapping[HostKey, Provider],
    on_error: OnError,
) -> Iterator[AutocheckEntry]:
    try:
        plugin = plugins[check_plugin_name]
    except KeyError:
        console.warning("  Missing check plugin: '%s'\n" % check_plugin_name)
        return

    try:
        kwargs = get_section_kwargs(providers, host_key, plugin.sections)
    except Exception as exc:
        if cmk.utils.debug.enabled() or on_error is OnError.RAISE:
            raise
        if on_error is OnError.WARN:
            console.warning("  Exception while parsing agent section: %s\n" % exc)
        return

    if not kwargs:
        return

    disco_params = plugin.parameters(host_key.hostname)
    if disco_params is not None:
        kwargs = {**kwargs, "params": disco_params}

    try:
        yield from (
            service.as_autocheck_entry(check_plugin_name) for service in plugin.function(**kwargs)
        )
    except Exception as e:
        if on_error is OnError.RAISE:
            raise
        if on_error is OnError.WARN:
            console.warning(
                "  Exception in discovery function of check plugin '%s': %s"
                % (check_plugin_name, e)
            )
