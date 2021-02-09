#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (
    Generator,
    Iterator,
    List,
    Optional,
    Set,
    Sequence,
)

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.misc
import cmk.utils.paths
from cmk.utils.check_utils import unwrap_parameters
from cmk.utils.exceptions import MKGeneralException, MKTimeout
from cmk.utils.log import console
from cmk.utils.type_defs import (
    CheckPluginName,
    HostAddress,
    HostName,
    ParsedSectionName,
    SourceType,
)

import cmk.core_helpers.cache

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.autochecks as autochecks
import cmk.base.check_api_utils as check_api_utils
import cmk.base.check_utils
import cmk.base.config as config
import cmk.base.core
import cmk.base.crash_reporting
import cmk.base.decorator
import cmk.base.section as section
import cmk.base.utils
from cmk.base.api.agent_based import checking_classes
from cmk.base.check_utils import Service
from cmk.base.sources.host_sections import HostKey, ParsedSectionsBroker
from cmk.base.discovered_labels import (
    DiscoveredServiceLabels,
    ServiceLabel,
)

from .type_defs import DiscoveryParameters
from .utils import QualifiedDiscovery


def analyse_discovered_services(
        *,
        host_name: HostName,
        ipaddress: Optional[HostAddress],
        parsed_sections_broker: ParsedSectionsBroker,
        discovery_parameters: DiscoveryParameters,
        run_only_plugin_names: Optional[Set[CheckPluginName]],
        only_new: bool,  # TODO: find a better name downwards in the callstack
) -> QualifiedDiscovery[Service]:

    if discovery_parameters.only_host_labels:
        # TODO: don't even come here, if there's nothing to do!
        existing = _load_existing_services(host_name=host_name)
        return QualifiedDiscovery(
            preexisting=existing,
            current=existing,
            key=lambda s: s.id(),
        )

    return _analyse_discovered_services(
        existing_services=_load_existing_services(host_name=host_name),
        discovered_services=_discover_services(
            host_name=host_name,
            ipaddress=ipaddress,
            parsed_sections_broker=parsed_sections_broker,
            discovery_parameters=discovery_parameters,
            run_only_plugin_names=run_only_plugin_names,
        ),
        run_only_plugin_names=run_only_plugin_names,
        only_new=only_new,
    )


def _analyse_discovered_services(
    *,
    existing_services: Sequence[Service],
    discovered_services: List[Service],
    run_only_plugin_names: Optional[Set[CheckPluginName]],
    only_new: bool,
) -> QualifiedDiscovery[Service]:

    return QualifiedDiscovery(
        preexisting=existing_services,
        current=discovered_services + _services_to_keep(
            choose_from=existing_services,
            run_only_plugin_names=run_only_plugin_names,
            only_new=only_new,
        ),
        key=lambda s: s.id(),
    )


def _services_to_keep(
    *,
    choose_from: Sequence[Service],
    only_new: bool,
    run_only_plugin_names: Optional[Set[CheckPluginName]],
) -> List[Service]:
    # There are tree ways of how to merge existing and new discovered checks:
    # 1. -II without --plugins=
    #        check_plugin_names is None, only_new is False
    #    --> completely drop old services, only use new ones
    if not only_new:
        if not run_only_plugin_names:
            return []
    # 2. -II with --plugins=
    #        check_plugin_names is not empty, only_new is False
    #    --> keep all services of other plugins
        return [s for s in choose_from if s.check_plugin_name not in run_only_plugin_names]
    # 3. -I
    #    --> just add new services
    #        only_new is True
    return list(choose_from)


def _load_existing_services(
    *,
    host_name: HostName,
) -> Sequence[Service]:
    return autochecks.parse_autochecks_file(host_name, config.service_description)


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
    discovery_parameters: DiscoveryParameters,
    run_only_plugin_names: Optional[Set[CheckPluginName]],
) -> List[Service]:
    # find out which plugins we need to discover
    plugin_candidates = _find_candidates(parsed_sections_broker, run_only_plugin_names)
    section.section_step("Executing discovery plugins (%d)" % len(plugin_candidates))
    console.vverbose("  Trying discovery with: %s\n" % ", ".join(str(n) for n in plugin_candidates))
    # The host name must be set for the host_name() calls commonly used to determine the
    # host name for host_extra_conf{_merged,} calls in the legacy checks.
    check_api_utils.set_hostname(host_name)

    service_table: cmk.base.check_utils.CheckTable = {}
    try:
        for check_plugin_name in plugin_candidates:
            try:
                service_table.update({
                    service.id(): service for service in _discover_plugins_services(
                        check_plugin_name=check_plugin_name,
                        host_name=host_name,
                        ipaddress=ipaddress,
                        parsed_sections_broker=parsed_sections_broker,
                        discovery_parameters=discovery_parameters,
                    )
                })
            except (KeyboardInterrupt, MKTimeout):
                raise
            except Exception as e:
                if discovery_parameters.on_error == "raise":
                    raise
                if discovery_parameters.on_error == "warn":
                    console.error("Discovery of '%s' failed: %s\n" % (check_plugin_name, e))

        return list(service_table.values())

    except KeyboardInterrupt:
        raise MKGeneralException("Interrupted by Ctrl-C.")


def _find_candidates(
    broker: ParsedSectionsBroker,
    run_only_plugin_names: Optional[Set[CheckPluginName]],
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
    if run_only_plugin_names is None:
        preliminary_candidates = list(agent_based_register.iter_all_check_plugins())
    else:
        preliminary_candidates = [
            p for p in agent_based_register.iter_all_check_plugins()
            if p.name in run_only_plugin_names
        ]

    parsed_sections_of_interest = {
        parsed_section_name for plugin in preliminary_candidates
        for parsed_section_name in plugin.sections
    }

    return (_find_host_candidates(broker, preliminary_candidates, parsed_sections_of_interest) |
            _find_mgmt_candidates(broker, preliminary_candidates, parsed_sections_of_interest))


def _find_host_candidates(
    broker: ParsedSectionsBroker,
    preliminary_candidates: List[checking_classes.CheckPlugin],
    parsed_sections_of_interest: Set[ParsedSectionName],
) -> Set[CheckPluginName]:

    available_parsed_sections = {
        s.parsed_section_name for s in broker.determine_applicable_sections(
            parsed_sections_of_interest,
            SourceType.HOST,
        )
    }

    return {
        plugin.name
        for plugin in preliminary_candidates
        # *filter out* all names of management only check plugins
        if not plugin.name.is_management_name() and any(
            section in available_parsed_sections for section in plugin.sections)
    }


def _find_mgmt_candidates(
    broker: ParsedSectionsBroker,
    preliminary_candidates: List[checking_classes.CheckPlugin],
    parsed_sections_of_interest: Set[ParsedSectionName],
) -> Set[CheckPluginName]:

    available_parsed_sections = {
        s.parsed_section_name for s in broker.determine_applicable_sections(
            parsed_sections_of_interest,
            SourceType.MANAGEMENT,
        )
    }

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
    discovery_parameters: DiscoveryParameters,
) -> Iterator[Service]:
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
        kwargs = parsed_sections_broker.get_section_kwargs(host_key, check_plugin.sections)
    except Exception as exc:
        if cmk.utils.debug.enabled() or discovery_parameters.on_error == "raise":
            raise
        if discovery_parameters.on_error == "warn":
            console.warning("  Exception while parsing agent section: %s\n" % exc)
        return
    if not kwargs:
        return

    disco_params = config.get_discovery_parameters(host_name, check_plugin)
    if disco_params is not None:
        kwargs["params"] = disco_params

    try:
        plugins_services = check_plugin.discovery_function(**kwargs)
        yield from _enriched_discovered_services(host_name, check_plugin.name, plugins_services)
    except Exception as e:
        if discovery_parameters.on_error == "warn":
            console.warning("  Exception in discovery function of check plugin '%s': %s" %
                            (check_plugin.name, e))
        elif discovery_parameters.on_error == "raise":
            raise


def _enriched_discovered_services(
    host_name: HostName,
    check_plugin_name: CheckPluginName,
    plugins_services: checking_classes.DiscoveryResult,
) -> Generator[Service, None, None]:
    for service in plugins_services:
        description = config.service_description(host_name, check_plugin_name, service.item)
        # make sanity check
        if not description:
            console.error(
                f"{host_name}: {check_plugin_name} returned empty service description - ignoring it.\n"
            )
            continue

        yield Service(
            check_plugin_name=check_plugin_name,
            item=service.item,
            description=description,
            parameters=unwrap_parameters(service.parameters),
            # Convert from APIs ServiceLabel to internal ServiceLabel
            service_labels=DiscoveredServiceLabels(*(ServiceLabel(*l) for l in service.labels)),
        )
