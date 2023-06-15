#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Container, Iterable, Iterator, Mapping, MutableMapping, Sequence

import cmk.utils.debug
import cmk.utils.misc
import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException, MKTimeout, OnError
from cmk.utils.log import console, section
from cmk.utils.type_defs import HostName

from cmk.checkengine import DiscoveryPlugin, HostKey, plugin_contexts, SourceType
from cmk.checkengine.check_table import ServiceID
from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.discovery import AutocheckEntry, AutochecksStore, QualifiedDiscovery
from cmk.checkengine.sectionparser import ParsedSectionName, Provider
from cmk.checkengine.sectionparserutils import get_section_kwargs

from cmk.base.config import ConfigCache


def analyse_discovered_services(
    config_cache: ConfigCache,
    host_name: HostName,
    *,
    providers: Mapping[HostKey, Provider],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    run_plugin_names: Container[CheckPluginName],
    forget_existing: bool,
    keep_vanished: bool,
    on_error: OnError,
) -> QualifiedDiscovery[AutocheckEntry]:
    return _analyse_discovered_services(
        existing_services=AutochecksStore(host_name).read(),
        discovered_services=_discover_services(
            config_cache,
            host_name,
            providers=providers,
            plugins=plugins,
            run_plugin_names=run_plugin_names,
            on_error=on_error,
        ),
        run_plugin_names=run_plugin_names,
        forget_existing=forget_existing,
        keep_vanished=keep_vanished,
    )


def _analyse_discovered_services(
    *,
    existing_services: Sequence[AutocheckEntry],
    discovered_services: list[AutocheckEntry],
    run_plugin_names: Container[CheckPluginName],
    forget_existing: bool,
    keep_vanished: bool,
) -> QualifiedDiscovery[AutocheckEntry]:
    return QualifiedDiscovery(
        preexisting=_services_to_remember(
            choose_from=existing_services,
            run_plugin_names=run_plugin_names,
            forget_existing=forget_existing,
        ),
        current=discovered_services
        + _services_to_keep(
            choose_from=existing_services,
            run_plugin_names=run_plugin_names,
            keep_vanished=keep_vanished,
        ),
    )


def _services_to_remember(
    *,
    choose_from: Sequence[AutocheckEntry],
    run_plugin_names: Container[CheckPluginName],
    forget_existing: bool,
) -> Sequence[AutocheckEntry]:
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
) -> list[AutocheckEntry]:
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
) -> list[AutocheckEntry]:
    return [s for s in services if s.check_plugin_name not in plugin_names]


def _discover_services(
    config_cache: ConfigCache,
    host_name: HostName,
    *,
    providers: Mapping[HostKey, Provider],
    run_plugin_names: Container[CheckPluginName],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    on_error: OnError,
) -> list[AutocheckEntry]:
    # find out which plugins we need to discover
    plugin_candidates = _find_candidates(
        providers,
        [
            (plugin_name, plugin.sections)
            for plugin_name, plugin in plugins.items()
            if plugin_name in run_plugin_names
        ],
    )
    section.section_step("Executing discovery plugins (%d)" % len(plugin_candidates))
    console.vverbose("  Trying discovery with: %s\n" % ", ".join(str(n) for n in plugin_candidates))
    # The host name must be set for the host_name() calls commonly used to determine the
    # host name for host_extra_conf{_merged,} calls in the legacy checks.

    service_table: MutableMapping[ServiceID, AutocheckEntry] = {}
    try:
        with plugin_contexts.current_host(host_name):
            for check_plugin_name in plugin_candidates:
                try:
                    service_table.update(
                        {
                            entry.id(): entry
                            for entry in _discover_plugins_services(
                                config_cache,
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

            return list(service_table.values())

    except KeyboardInterrupt:
        raise MKGeneralException("Interrupted by Ctrl-C.")


def _find_candidates(
    providers: Mapping[HostKey, Provider],
    preliminary_candidates: Sequence[tuple[CheckPluginName, Sequence[ParsedSectionName]]],
) -> set[CheckPluginName]:
    """Return names of check plugins that this multi_host_section may
    contain data for.

    Given this mutli_host_section, there is no point in trying to discover
    any check plugins not returned by this function.  This does not
    address the question whether or not the returned check plugins will
    discover something.

    We have to consider both the host, and the management board as source
    type. Note that the determination of the plugin names is not quite
    symmetric: For the host, we filter out all management plugins,
    for the management board we create management variants from all
    plugins that are not already designed for management boards.

    """

    def __iter(
        section_names: Iterable[ParsedSectionName], providers: Mapping[HostKey, Provider]
    ) -> Iterable[tuple[HostKey, ParsedSectionName]]:
        for host_key, provider in providers.items():
            # filter section names for sections that cannot be resolved
            for section_name in (
                section_name
                for section_name in section_names
                if provider.resolve(section_name) is not None
            ):
                yield host_key, section_name

    parsed_sections_of_interest: Sequence[ParsedSectionName] = list(
        frozenset(
            itertools.chain.from_iterable(sections for (_name, sections) in preliminary_candidates)
        )
    )
    resolved: Sequence[tuple[HostKey, ParsedSectionName]] = tuple(
        __iter(parsed_sections_of_interest, providers)
    )

    return _find_host_candidates(
        preliminary_candidates,
        frozenset(
            section_name
            for host_key, section_name in resolved
            if host_key.source_type is SourceType.HOST
        ),
    ) | _find_mgmt_candidates(
        preliminary_candidates,
        frozenset(
            section_name
            for host_key, section_name in resolved
            if host_key.source_type is SourceType.MANAGEMENT
        ),
    )


def _find_host_candidates(
    preliminary_candidates: Iterable[tuple[CheckPluginName, Iterable[ParsedSectionName]]],
    available_parsed_sections: Container[ParsedSectionName],
) -> set[CheckPluginName]:
    return {
        name
        for (name, sections) in preliminary_candidates
        # *filter out* all names of management only check plugins
        if not name.is_management_name()
        and any(section in available_parsed_sections for section in sections)
    }


def _find_mgmt_candidates(
    preliminary_candidates: Iterable[tuple[CheckPluginName, Iterable[ParsedSectionName]]],
    available_parsed_sections: Container[ParsedSectionName],
) -> set[CheckPluginName]:
    return {
        # *create* all management only names of the plugins
        name.create_management_name()
        for (name, sections) in preliminary_candidates
        if any(section in available_parsed_sections for section in sections)
    }


def _discover_plugins_services(
    config_cache: ConfigCache,
    *,
    check_plugin_name: CheckPluginName,
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    host_key: HostKey,
    providers: Mapping[HostKey, Provider],
    on_error: OnError,
) -> Iterator[AutocheckEntry]:
    # Skip this check type if is ignored for that host
    if config_cache.check_plugin_ignored(host_key.hostname, check_plugin_name):
        console.vverbose("  Skip ignored check plugin name '%s'\n" % check_plugin_name)
        return

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
