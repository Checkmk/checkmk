#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
import sys
from collections.abc import Container, Iterable, Iterator, Mapping, Sequence

import cmk.ccc.debug
from cmk.ccc import tty
from cmk.ccc.exceptions import MKTimeout, OnError
from cmk.ccc.hostaddress import HostName

from cmk.utils.log import console

from cmk.checkengine.fetcher import HostKey, SourceType
from cmk.checkengine.plugins import AutocheckEntry, CheckPluginName, DiscoveryPlugin, ServiceID
from cmk.checkengine.sectionparser import ParsedSectionName, Provider
from cmk.checkengine.sectionparserutils import get_section_kwargs

from ._utils import QualifiedDiscovery

__all__ = ["analyse_services", "discover_services", "find_plugins"]


def find_plugins(
    providers: Mapping[HostKey, Provider],
    preliminary_candidates: Sequence[tuple[CheckPluginName, Sequence[ParsedSectionName]]],
) -> set[CheckPluginName]:
    """Return names of check plug-ins that this multi_host_section may
    contain data for.

    Given this mutli_host_section, there is no point in trying to discover
    any check plug-ins not returned by this function.  This does not
    address the question whether or not the returned check plug-ins will
    discover something.

    We have to consider both the host, and the management board as source
    type. Note that the determination of the plug-in names is not quite
    symmetric: For the host, we filter out all management plug-ins,
    for the management board we create management variants from all
    plugins that are not already designed for management boards.

    """

    def __iter(
        section_names: Iterable[ParsedSectionName], providers: Iterable[Provider]
    ) -> Iterable[ParsedSectionName]:
        for provider in providers:
            # filter section names for sections that cannot be resolved
            yield from (
                section_name
                for section_name in section_names
                if provider.resolve(section_name) is not None
            )

    parsed_sections_of_interest = frozenset(
        itertools.chain.from_iterable(sections for (_name, sections) in preliminary_candidates)
    )

    return _find_host_plugins(
        preliminary_candidates,
        frozenset(
            __iter(
                parsed_sections_of_interest,
                (
                    provider
                    for (host_key, provider) in providers.items()
                    if host_key.source_type is SourceType.HOST
                ),
            )
        ),
    ) | _find_mgmt_plugins(
        preliminary_candidates,
        frozenset(
            __iter(
                parsed_sections_of_interest,
                (
                    provider
                    for (host_key, provider) in providers.items()
                    if host_key.source_type is SourceType.MANAGEMENT
                ),
            )
        ),
    )


def _find_host_plugins(
    preliminary_candidates: Iterable[tuple[CheckPluginName, Iterable[ParsedSectionName]]],
    available_parsed_sections: Container[ParsedSectionName],
) -> set[CheckPluginName]:
    return {
        name
        for (name, sections) in preliminary_candidates
        # *filter out* all names of management only check plug-ins
        if not name.is_management_name()
        and any(section in available_parsed_sections for section in sections)
    }


def _find_mgmt_plugins(
    preliminary_candidates: Iterable[tuple[CheckPluginName, Iterable[ParsedSectionName]]],
    available_parsed_sections: Container[ParsedSectionName],
) -> set[CheckPluginName]:
    return {
        # *create* all management only names of the plugins
        name.create_management_name()
        for (name, sections) in preliminary_candidates
        if any(section in available_parsed_sections for section in sections)
    }


def discover_services(
    host_name: HostName,
    plugin_names: Iterable[CheckPluginName],
    *,
    providers: Mapping[HostKey, Provider],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    on_error: OnError,
) -> Sequence[AutocheckEntry]:
    service_table: dict[ServiceID, AutocheckEntry] = {}
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
                console.error(f"Discovery of '{check_plugin_name}' failed: {e}", file=sys.stderr)

    # TODO: Building a dict to discard its keys isn't efficient.
    # (this currently deduplicates items. Could be done on a per-plugin basis.)
    return list(service_table.values())


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
        console.warning(tty.format_warning(f"  Missing check plug-in: '{check_plugin_name}'\n"))
        return

    try:
        kwargs = get_section_kwargs(providers, host_key, plugin.sections)
    except Exception as exc:
        if cmk.ccc.debug.enabled() or on_error is OnError.RAISE:
            raise
        if on_error is OnError.WARN:
            console.warning(tty.format_warning(f"  Exception while parsing agent section: {exc}\n"))
        return

    if not kwargs:
        return

    disco_params = plugin.parameters(host_key.hostname)
    if disco_params is not None:
        kwargs = {**kwargs, "params": disco_params}

    try:
        yield from plugin.function(check_plugin_name, **kwargs)
    except Exception as e:
        if on_error is OnError.RAISE:
            raise
        if on_error is OnError.WARN:
            console.warning(
                tty.format_warning(
                    f"  Exception in discovery function of check plug-in '{check_plugin_name}': {e}"
                )
            )


def analyse_services(
    *,
    existing_services: Sequence[AutocheckEntry],
    discovered_services: Iterable[AutocheckEntry],
    run_plugin_names: Container[CheckPluginName],
    forget_existing: bool,
    keep_vanished: bool,
) -> QualifiedDiscovery[AutocheckEntry]:
    return QualifiedDiscovery(
        preexisting=list(
            _services_to_remember(
                choose_from=existing_services,
                run_plugin_names=run_plugin_names,
                forget_existing=forget_existing,
            )
        ),
        current=list(
            itertools.chain(
                discovered_services,
                _services_to_keep(
                    choose_from=existing_services,
                    run_plugin_names=run_plugin_names,
                    keep_vanished=keep_vanished,
                ),
            )
        ),
    )


def _services_to_remember(
    *,
    choose_from: Sequence[AutocheckEntry],
    run_plugin_names: Container[CheckPluginName],
    forget_existing: bool,
) -> Iterable[AutocheckEntry]:
    """Compile a list of services to regard as being the last known state

    This list is used to classify services into new/old/vanished.
    Remembering is not the same as keeping!
    Always remember the services of plugins that are not being run.
    """
    return _drop_plugins_services(choose_from, run_plugin_names) if forget_existing else choose_from


def _services_to_keep(
    *,
    choose_from: Sequence[AutocheckEntry],
    run_plugin_names: Container[CheckPluginName],
    keep_vanished: bool,
) -> Iterable[AutocheckEntry]:
    """Compile a list of services to keep in addition to the discovered ones

    These services are considered to be currently present (even if they are not discovered).
    Always keep the services of plugins that are not being run.
    """
    return (
        list(choose_from)
        if keep_vanished
        else _drop_plugins_services(choose_from, run_plugin_names)
    )


def _drop_plugins_services(
    services: Sequence[AutocheckEntry],
    plugin_names: Container[CheckPluginName],
) -> Iterable[AutocheckEntry]:
    return (s for s in services if s.check_plugin_name not in plugin_names)
