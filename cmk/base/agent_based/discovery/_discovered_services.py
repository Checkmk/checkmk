#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Container, Generator, Iterator, List, MutableMapping, Optional, Sequence, Set

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.misc
import cmk.utils.paths
from cmk.utils.check_utils import unwrap_parameters
from cmk.utils.exceptions import MKGeneralException, MKTimeout, OnError
from cmk.utils.log import console
from cmk.utils.type_defs import (
    CheckPluginName,
    EVERYTHING,
    HostAddress,
    HostKey,
    HostName,
    ParsedSectionName,
    SourceType,
)

import cmk.core_helpers.cache

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.autochecks as autochecks
import cmk.base.config as config
import cmk.base.plugin_contexts as plugin_contexts
import cmk.base.section as section
from cmk.base.agent_based.data_provider import ParsedSectionsBroker
from cmk.base.agent_based.utils import get_section_kwargs
from cmk.base.api.agent_based import checking_classes
from cmk.base.check_utils import AutocheckService, ServiceID
from cmk.base.discovered_labels import ServiceLabel

from .utils import QualifiedDiscovery


def analyse_discovered_services(
    *,
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    parsed_sections_broker: ParsedSectionsBroker,
    run_plugin_names: Container[CheckPluginName],
    forget_existing: bool,
    keep_vanished: bool,
    on_error: OnError,
) -> QualifiedDiscovery[AutocheckService]:

    return _analyse_discovered_services(
        existing_services=_load_existing_services(host_name=host_name),
        discovered_services=_discover_services(
            host_name=host_name,
            ipaddress=ipaddress,
            parsed_sections_broker=parsed_sections_broker,
            run_plugin_names=run_plugin_names,
            on_error=on_error,
        ),
        run_plugin_names=run_plugin_names,
        forget_existing=forget_existing,
        keep_vanished=keep_vanished,
    )


def _analyse_discovered_services(
    *,
    existing_services: Sequence[AutocheckService],
    discovered_services: List[AutocheckService],
    run_plugin_names: Container[CheckPluginName],
    forget_existing: bool,
    keep_vanished: bool,
) -> QualifiedDiscovery[AutocheckService]:

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
        key=lambda s: s.id(),
    )


def _services_to_remember(
    *,
    choose_from: Sequence[AutocheckService],
    run_plugin_names: Container[CheckPluginName],
    forget_existing: bool,
) -> Sequence[AutocheckService]:
    """Compile a list of services to regard as being the last known state

    This list is used to classify services into new/old/vanished.
    Remembering is not the same as keeping!
    Always remember the services of plugins that are not being run.
    """
    return _drop_plugins_services(choose_from, run_plugin_names) if forget_existing else choose_from


def _services_to_keep(
    *,
    choose_from: Sequence[AutocheckService],
    run_plugin_names: Container[CheckPluginName],
    keep_vanished: bool,
) -> List[AutocheckService]:
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
    services: Sequence[AutocheckService],
    plugin_names: Container[CheckPluginName],
) -> List[AutocheckService]:
    return (
        []
        if plugin_names is EVERYTHING
        else [s for s in services if s.check_plugin_name not in plugin_names]
    )


def _load_existing_services(
    *,
    host_name: HostName,
) -> Sequence[AutocheckService]:
    return autochecks.parse_autochecks_services(host_name, config.service_description)


# Create a table of autodiscovered services of a host. Do not save
# this table anywhere. Do not read any previously discovered
# services. The table has the following columns:
# 1. Check type
# 2. Item
# 3. Parameter string (not evaluated)
#
# This function does not handle:
# - clusters
# - disabled services
#
# This function *does* handle:
# - disabled check typess
#
# on_error is one of:
# "ignore" -> silently ignore any exception
# "warn"   -> output a warning on stderr
# "raise"  -> let the exception come through
def _discover_services(
    *,
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    parsed_sections_broker: ParsedSectionsBroker,
    run_plugin_names: Container[CheckPluginName],
    on_error: OnError,
) -> List[AutocheckService]:
    # find out which plugins we need to discover
    plugin_candidates = _find_candidates(parsed_sections_broker, run_plugin_names)
    section.section_step("Executing discovery plugins (%d)" % len(plugin_candidates))
    console.vverbose("  Trying discovery with: %s\n" % ", ".join(str(n) for n in plugin_candidates))
    # The host name must be set for the host_name() calls commonly used to determine the
    # host name for host_extra_conf{_merged,} calls in the legacy checks.

    service_table: MutableMapping[ServiceID, AutocheckService] = {}
    try:
        with plugin_contexts.current_host(host_name):
            for check_plugin_name in plugin_candidates:
                try:
                    service_table.update(
                        {
                            service.id(): service
                            for service in _discover_plugins_services(
                                check_plugin_name=check_plugin_name,
                                host_name=host_name,
                                ipaddress=ipaddress,
                                parsed_sections_broker=parsed_sections_broker,
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
    broker: ParsedSectionsBroker,
    run_plugin_names: Container[CheckPluginName],
) -> Set[CheckPluginName]:
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
    if run_plugin_names is EVERYTHING:
        preliminary_candidates = list(agent_based_register.iter_all_check_plugins())
    else:
        preliminary_candidates = [
            p for p in agent_based_register.iter_all_check_plugins() if p.name in run_plugin_names
        ]

    parsed_sections_of_interest = {
        parsed_section_name
        for plugin in preliminary_candidates
        for parsed_section_name in plugin.sections
    }

    return _find_host_candidates(
        broker, preliminary_candidates, parsed_sections_of_interest
    ) | _find_mgmt_candidates(broker, preliminary_candidates, parsed_sections_of_interest)


def _find_host_candidates(
    broker: ParsedSectionsBroker,
    preliminary_candidates: List[checking_classes.CheckPlugin],
    parsed_sections_of_interest: Set[ParsedSectionName],
) -> Set[CheckPluginName]:

    available_parsed_sections = broker.filter_available(
        parsed_sections_of_interest,
        SourceType.HOST,
    )

    return {
        plugin.name
        for plugin in preliminary_candidates
        # *filter out* all names of management only check plugins
        if not plugin.name.is_management_name()
        and any(section in available_parsed_sections for section in plugin.sections)
    }


def _find_mgmt_candidates(
    broker: ParsedSectionsBroker,
    preliminary_candidates: List[checking_classes.CheckPlugin],
    parsed_sections_of_interest: Set[ParsedSectionName],
) -> Set[CheckPluginName]:

    available_parsed_sections = broker.filter_available(
        parsed_sections_of_interest,
        SourceType.MANAGEMENT,
    )

    return {
        # *create* all management only names of the plugins
        plugin.name.create_management_name()
        for plugin in preliminary_candidates
        if any(section in available_parsed_sections for section in plugin.sections)
    }


def _discover_plugins_services(
    *,
    check_plugin_name: CheckPluginName,
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    parsed_sections_broker: ParsedSectionsBroker,
    on_error: OnError,
) -> Iterator[AutocheckService]:
    # Skip this check type if is ignored for that host
    if config.service_ignored(host_name, check_plugin_name, None):
        console.vverbose("  Skip ignored check plugin name '%s'\n" % check_plugin_name)
        return

    check_plugin = agent_based_register.get_check_plugin(check_plugin_name)
    if check_plugin is None:
        console.warning("  Missing check plugin: '%s'\n" % check_plugin_name)
        return

    host_key = HostKey(
        host_name,
        ipaddress,
        SourceType.MANAGEMENT if check_plugin.name.is_management_name() else SourceType.HOST,
    )

    try:
        kwargs = get_section_kwargs(parsed_sections_broker, host_key, check_plugin.sections)
    except Exception as exc:
        if cmk.utils.debug.enabled() or on_error is OnError.RAISE:
            raise
        if on_error is OnError.WARN:
            console.warning("  Exception while parsing agent section: %s\n" % exc)
        return

    if not kwargs:
        return

    disco_params = config.get_discovery_parameters(host_name, check_plugin)
    if disco_params is not None:
        kwargs = {**kwargs, "params": disco_params}

    try:
        plugins_services = check_plugin.discovery_function(**kwargs)
        yield from _enriched_discovered_services(host_name, check_plugin.name, plugins_services)
    except Exception as e:
        if on_error is OnError.RAISE:
            raise
        if on_error is OnError.WARN:
            console.warning(
                "  Exception in discovery function of check plugin '%s': %s"
                % (check_plugin.name, e)
            )


def _enriched_discovered_services(
    host_name: HostName,
    check_plugin_name: CheckPluginName,
    plugins_services: checking_classes.DiscoveryResult,
) -> Generator[AutocheckService, None, None]:
    for service in plugins_services:
        description = config.service_description(host_name, check_plugin_name, service.item)
        # make sanity check
        if not description:
            console.error(
                f"{host_name}: {check_plugin_name} returned empty service description - ignoring it.\n"
            )
            continue

        yield AutocheckService(
            check_plugin_name=check_plugin_name,
            item=service.item,
            description=description,
            parameters=unwrap_parameters(service.parameters),
            # Convert from APIs ServiceLabel to internal ServiceLabel
            service_labels={name: ServiceLabel(name, value) for name, value in service.labels},
        )
