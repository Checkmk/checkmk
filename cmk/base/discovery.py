#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import signal
import socket
import time
from enum import Enum
from types import FrameType
from typing import (
    Any,
    Callable,
    Counter,
    Dict,
    Generator,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    NoReturn,
    Optional,
    Pattern,
    Sequence,
    Set,
    Tuple,
)

from six import ensure_binary

import livestatus

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.misc
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.caching import config_cache as _config_cache
from cmk.utils.check_utils import unwrap_parameters, wrap_parameters
from cmk.utils.exceptions import MKException, MKGeneralException, MKTimeout
from cmk.utils.labels import DiscoveredHostLabelsStore
from cmk.utils.log import console
from cmk.utils.object_diff import make_object_diff
from cmk.utils.regex import regex
from cmk.utils.type_defs import (
    CheckPluginName,
    CheckPluginNameStr,
    DiscoveryResult,
    HostAddress,
    HostName,
    HostState,
    Item,
    MetricTuple,
    ParsedSectionName,
    RulesetName,
    SectionName,
    SourceType,
    state_markers,
)

import cmk.core_helpers.cache
from cmk.core_helpers.protocol import FetcherMessage
from cmk.core_helpers.type_defs import Mode, NO_SELECTION, SectionNameCollection

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.autochecks as autochecks
import cmk.base.check_api_utils as check_api_utils
import cmk.base.check_table as check_table
import cmk.base.check_utils
import cmk.base.sources as sources
import cmk.base.checking as checking
import cmk.base.config as config
import cmk.base.core
import cmk.base.crash_reporting
import cmk.base.decorator
import cmk.base.ip_lookup as ip_lookup
import cmk.base.section as section
import cmk.base.utils
from cmk.base.api.agent_based import checking_classes
from cmk.base.api.agent_based.type_defs import Parameters
from cmk.base.autochecks import ServiceWithNodes
from cmk.base.check_utils import LegacyCheckParameters, Service, ServiceID
from cmk.base.sources.host_sections import HostKey, ParsedSectionsBroker
from cmk.base.core_config import MonitoringCore
from cmk.base.discovered_labels import (
    DiscoveredHostLabels,
    DiscoveredHostLabelsDict,
    DiscoveredServiceLabels,
    ServiceLabel,
)

# Run the discovery queued by check_discovery() - if any
_marked_host_discovery_timeout = 120

ServicesTable = Dict[ServiceID, Tuple[str, Service, List[HostName]]]
ServicesByTransition = Dict[str, List[ServiceWithNodes]]

CheckPreviewEntry = Tuple[str, CheckPluginNameStr, Optional[RulesetName], Item,
                          LegacyCheckParameters, LegacyCheckParameters, str, Optional[int], str,
                          List[MetricTuple], Dict[str, str], List[HostName]]
CheckPreviewTable = List[CheckPreviewEntry]
ServiceFilter = Callable[[HostName, Service], bool]
ServiceFilters = NamedTuple("ServiceFilters", [
    ("new", ServiceFilter),
    ("vanished", ServiceFilter),
])
ServiceFilterLists = NamedTuple("ServiceFilterLists", [
    ("new_whitelist", Optional[List[str]]),
    ("new_blacklist", Optional[List[str]]),
    ("vanished_whitelist", Optional[List[str]]),
    ("vanished_blacklist", Optional[List[str]]),
])


class RediscoveryMode(Enum):
    new = 0
    remove = 1
    fixall = 2
    refresh = 3


DiscoveryParameters = NamedTuple("DiscoveryParameters", [
    ("on_error", str),
    ("load_labels", bool),
    ("save_labels", bool),
    ("only_host_labels", bool),
])

HostLabelDiscoveryResult = NamedTuple("HostLabelDiscoveryResult", [
    ("labels", DiscoveredHostLabels),
    ("per_plugin", Counter[str]),
])

#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   |  Various helper functions                                            |
#   '----------------------------------------------------------------------'


# TODO: Move to livestatus module!
def schedule_discovery_check(host_name: HostName) -> None:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(cmk.utils.paths.livestatus_unix_socket)
        now = int(time.time())
        if 'cmk_inventory' in config.use_new_descriptions_for:
            command = "SCHEDULE_FORCED_SVC_CHECK;%s;Check_MK Discovery;%d" % (host_name, now)
        else:
            # TODO: Remove this old name handling one day
            command = "SCHEDULE_FORCED_SVC_CHECK;%s;Check_MK inventory;%d" % (host_name, now)

        # Ignore missing check and avoid warning in cmc.log
        if config.monitoring_core == "cmc":
            command += ";TRY"

        s.send(ensure_binary("COMMAND [%d] %s\n" % (now, command)))
    except Exception:
        if cmk.utils.debug.enabled():
            raise


def get_service_filter_funcs(params: Dict[str, Any]) -> ServiceFilters:
    service_filter_lists = _get_service_filter_lists(params)

    new_services_filter = _get_service_filter_func(
        service_filter_lists.new_whitelist,
        service_filter_lists.new_blacklist,
    )

    vanished_services_filter = _get_service_filter_func(
        service_filter_lists.vanished_whitelist,
        service_filter_lists.vanished_blacklist,
    )

    return ServiceFilters(new_services_filter, vanished_services_filter)


def _get_service_filter_lists(params: Dict[str, Any]) -> ServiceFilterLists:
    rediscovery_parameters = _get_rediscovery_parameters(params)

    if "service_filters" not in rediscovery_parameters:
        # Be compatible to pre 1.7.0 versions; There were only two general pattern lists
        # which were used for new AND vanished services:
        # {
        #     "service_whitelist": [PATTERN],
        #     "service_blacklist": [PATTERN],
        # }
        service_whitelist = rediscovery_parameters.get("service_whitelist")
        service_blacklist = rediscovery_parameters.get("service_blacklist")
        return ServiceFilterLists(
            service_whitelist,
            service_blacklist,
            service_whitelist,
            service_blacklist,
        )

    # New since 1.7.0: A white- and blacklist can be configured for both new and vanished
    # services as "combined" pattern lists.
    # Or two separate pattern lists for each new and vanished services are configurable:
    # {
    #     "service_filters": (
    #         "combined",
    #         {
    #             "service_whitelist": [PATTERN],
    #             "service_blacklist": [PATTERN],
    #         },
    #     )
    # } resp.
    # {
    #     "service_filters": (
    #         "dedicated",
    #         {
    #             "service_whitelist": [PATTERN],
    #             "service_blacklist": [PATTERN],
    #             "vanished_service_whitelist": [PATTERN],
    #             "vanished_service_blacklist": [PATTERN],
    #         },
    #     )
    # }
    service_filter_ty, service_filter_lists = rediscovery_parameters["service_filters"]

    if service_filter_ty == "combined":
        new_service_whitelist = service_filter_lists.get("service_whitelist")
        new_service_blacklist = service_filter_lists.get("service_blacklist")
        return ServiceFilterLists(
            new_service_whitelist,
            new_service_blacklist,
            new_service_whitelist,
            new_service_blacklist,
        )

    if service_filter_ty == "dedicated":
        return ServiceFilterLists(
            service_filter_lists.get("service_whitelist"),
            service_filter_lists.get("service_blacklist"),
            service_filter_lists.get("vanished_service_whitelist"),
            service_filter_lists.get("vanished_service_blacklist"),
        )

    raise NotImplementedError()


def _get_service_filter_func(service_whitelist: Optional[List[str]],
                             service_blacklist: Optional[List[str]]) -> ServiceFilter:
    if not service_whitelist and not service_blacklist:
        return _accept_all_services

    if not service_whitelist:
        # whitelist. if none is specified, this matches everything
        service_whitelist = [".*"]

    if not service_blacklist:
        # blacklist. if none is specified, this matches nothing
        service_blacklist = ["(?!x)x"]

    whitelist = regex("|".join(["(%s)" % p for p in service_whitelist]))
    blacklist = regex("|".join(["(%s)" % p for p in service_blacklist]))

    return lambda host_name, service: _filter_service_by_patterns(host_name, service, whitelist,
                                                                  blacklist)


def _filter_service_by_patterns(
    host_name: HostName,
    service: Service,
    whitelist: Pattern[str],
    blacklist: Pattern[str],
) -> bool:
    #TODO Call sites: Why do we not use discovered_service.description;
    # Is discovered_service.description already finalized as
    # in config.service_description?
    # (mo): we should indeed make sure that is the case, and use it
    description = config.service_description(host_name, service.check_plugin_name, service.item)
    return whitelist.match(description) is not None and blacklist.match(description) is None


def _accept_all_services(_host_name: HostName, _service: Service) -> bool:
    return True


def _get_rediscovery_parameters(params: Dict) -> Dict:
    return params.get("inventory_rediscovery", {})


def _get_rediscovery_mode(params: Dict) -> str:
    mode_int = _get_rediscovery_parameters(params).get("mode")
    try:
        return RediscoveryMode(mode_int).name
    except ValueError:
        return ""


#.
#   .--cmk -I--------------------------------------------------------------.
#   |                                  _           ___                     |
#   |                    ___ _ __ ___ | | __      |_ _|                    |
#   |                   / __| '_ ` _ \| |/ /  _____| |                     |
#   |                  | (__| | | | | |   <  |_____| |                     |
#   |                   \___|_| |_| |_|_|\_\      |___|                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Functions for command line options -I and -II                       |
#   '----------------------------------------------------------------------'


# Function implementing cmk -I and cmk -II. This is directly
# being called from the main option parsing code. The list of
# hostnames is already prepared by the main code. If it is
# empty then we use all hosts and switch to using cache files.
def do_discovery(
    arg_hostnames: Set[HostName],
    *,
    selected_sections: SectionNameCollection,
    run_only_plugin_names: Optional[Set[CheckPluginName]],
    arg_only_new: bool,
    only_host_labels: bool = False,
) -> None:
    config_cache = config.get_config_cache()
    use_caches = not arg_hostnames or cmk.core_helpers.cache.FileCacheFactory.maybe
    on_error = "raise" if cmk.utils.debug.enabled() else "warn"

    discovery_parameters = DiscoveryParameters(
        on_error=on_error,
        load_labels=arg_only_new,
        save_labels=True,
        only_host_labels=only_host_labels,
    )

    host_names = _preprocess_hostnames(arg_hostnames, config_cache, only_host_labels)

    mode = Mode.DISCOVERY if selected_sections is NO_SELECTION else Mode.FORCE_SECTIONS

    # Now loop through all hosts
    for host_name in sorted(host_names):
        host_config = config_cache.get_host_config(host_name)
        section.section_begin(host_name)
        try:
            ipaddress = ip_lookup.lookup_ip_address(
                host_config,
                family=host_config.default_address_family,
            )
            nodes = sources.make_nodes(
                config_cache,
                host_config,
                ipaddress,
                mode,
                sources.make_sources(
                    host_config,
                    ipaddress,
                    mode=mode,
                    selected_sections=selected_sections,
                    on_scan_error=on_error,
                ),
            )
            max_cachefile_age = config.discovery_max_cachefile_age(use_caches)

            parsed_sections_broker = ParsedSectionsBroker()
            sources.update_host_sections(
                parsed_sections_broker,
                nodes,
                max_cachefile_age=max_cachefile_age,
                host_config=host_config,
                fetcher_messages=list(
                    sources.fetch_all(
                        nodes,
                        max_cachefile_age=max_cachefile_age,
                        host_config=host_config,
                    )),
                selected_sections=selected_sections,
            )
            _do_discovery_for(
                host_name,
                ipaddress,
                parsed_sections_broker,
                run_only_plugin_names,
                arg_only_new,
                discovery_parameters,
            )

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            section.section_error("%s" % e)
        finally:
            cmk.utils.cleanup.cleanup_globals()


def _preprocess_hostnames(
    arg_host_names: Set[HostName],
    config_cache: config.ConfigCache,
    only_host_labels: bool,
) -> Set[HostName]:
    """Default to all hosts and expand cluster names to their nodes"""
    if not arg_host_names:
        console.verbose("Discovering %shost labels on all hosts\n" %
                        ("services and " if not only_host_labels else ""))
        arg_host_names = config_cache.all_active_realhosts()
    else:
        console.verbose(
            "Discovering %shost labels on: %s\n" %
            ("services and " if not only_host_labels else "", ", ".join(sorted(arg_host_names))))

    host_names: Set[HostName] = set()
    # For clusters add their nodes to the list. Clusters itself
    # cannot be discovered but the user is allowed to specify
    # them and we do discovery on the nodes instead.
    for host_name, host_config in [(hn, config_cache.get_host_config(hn)) for hn in arg_host_names]:
        if not host_config.is_cluster:
            host_names.add(host_name)
            continue

        if host_config.nodes is None:
            raise MKGeneralException("Invalid cluster configuration")
        host_names.update(host_config.nodes)

    return host_names


def _do_discovery_for(
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    parsed_sections_broker: ParsedSectionsBroker,
    run_only_plugin_names: Optional[Set[CheckPluginName]],
    only_new: bool,
    discovery_parameters: DiscoveryParameters,
) -> None:

    discovered_services, host_label_discovery_result = _discover_host_labels_and_services(
        host_name=host_name,
        ipaddress=ipaddress,
        parsed_sections_broker=parsed_sections_broker,
        discovery_parameters=discovery_parameters,
        run_only_plugin_names=run_only_plugin_names,
    )

    new_services = _load_existing_services(
        host_name=host_name,
        only_new=only_new,
        run_only_plugin_names=run_only_plugin_names,
    )

    services_per_plugin: Counter[CheckPluginName] = Counter()
    for discovered_service in discovered_services:
        if discovered_service not in new_services:
            new_services.append(discovered_service)
            services_per_plugin[discovered_service.check_plugin_name] += 1

    autochecks.save_autochecks_file(host_name, new_services)

    messages = []

    if services_per_plugin:
        for check_plugin_name, count in sorted(services_per_plugin.items()):
            console.verbose("%s%3d%s %s\n" %
                            (tty.green + tty.bold, count, tty.normal, check_plugin_name))
        messages.append("Found %d services" % sum(services_per_plugin.values()))
    else:
        messages.append("Found no%s services" % (only_new and " new" or ""))

    if host_label_discovery_result.per_plugin:
        messages.append("%d host labels" % sum(host_label_discovery_result.per_plugin.values()))
    else:
        messages.append("no%s host labels" % (only_new and " new" or ""))

    section.section_success(", ".join(messages))


def _load_existing_services(
    *,
    host_name: HostName,
    only_new: bool,
    run_only_plugin_names: Optional[Set[CheckPluginName]],
) -> List[Service]:
    # There are four ways of how to merge existing and new discovered checks:
    # 1. -II without --checks=
    #        check_plugin_names is empty, only_new is False
    #    --> complete drop old services, only use new ones
    # 2. -II with --checks=
    #    --> drop old services of that types
    #        check_plugin_names is not empty, only_new is False
    # 3. -I
    #    --> just add new services
    #        only_new is True
    # 4. -I --only-host-labels
    #    --> only discover new host labels
    if not run_only_plugin_names and not only_new:
        return []

    autocheck_services = autochecks.parse_autochecks_file(host_name, config.service_description)

    # Take over old items if -I is selected ...
    if only_new:
        return autocheck_services

    # ... or if -II is selected with --plugins= and the check type is not one of the listed ones
    assert run_only_plugin_names
    return [s for s in autocheck_services if s.check_plugin_name not in run_only_plugin_names]


# determine changed services on host.
# param mode: can be one of "new", "remove", "fixall", "refresh", "only-host-labels"
# param servic_filter: if a filter is set, it controls whether items are touched by the discovery.
#                       if it returns False for a new item it will not be added, if it returns
#                       False for a vanished item, that item is kept
def discover_on_host(
    config_cache: config.ConfigCache,
    host_config: config.HostConfig,
    mode: str,
    use_caches: bool,
    service_filters: ServiceFilters,
    on_error: str = "ignore",
) -> DiscoveryResult:

    console.verbose("  Doing discovery with mode '%s'...\n" % mode)

    host_name = host_config.hostname
    result = DiscoveryResult()
    discovery_parameters = DiscoveryParameters(
        on_error=on_error,
        load_labels=(mode != "remove"),
        save_labels=(mode != "remove"),
        only_host_labels=(mode == "only-host-labels"),
    )

    if host_name not in config_cache.all_active_hosts():
        result.error_text = ""
        return result

    host_label_discovery_result = HostLabelDiscoveryResult(
        labels=DiscoveredHostLabels(),
        per_plugin=Counter(),
    )

    try:
        # in "refresh" mode we first need to remove all previously discovered
        # checks of the host, so that _get_host_services() does show us the
        # new discovered check parameters.
        if mode == "refresh":
            result.self_removed += host_config.remove_autochecks()  # this is cluster-aware!

        if host_config.is_cluster:
            ipaddress = None
        else:
            ipaddress = ip_lookup.lookup_ip_address(
                host_config,
                family=host_config.default_address_family,
            )

        nodes = sources.make_nodes(
            config_cache,
            host_config,
            ipaddress,
            Mode.DISCOVERY,
            sources.make_sources(
                host_config,
                ipaddress,
                mode=Mode.DISCOVERY,
                on_scan_error=on_error,
            ),
        )

        max_cachefile_age = config.discovery_max_cachefile_age(use_caches)
        parsed_sections_broker = ParsedSectionsBroker()
        sources.update_host_sections(
            parsed_sections_broker,
            nodes,
            max_cachefile_age=max_cachefile_age,
            host_config=host_config,
            fetcher_messages=list(
                sources.fetch_all(
                    nodes,
                    max_cachefile_age=max_cachefile_age,
                    host_config=host_config,
                )),
            selected_sections=NO_SELECTION,
        )

        # Compute current state of new and existing checks
        services, host_label_discovery_result = _get_host_services(
            host_config,
            ipaddress,
            parsed_sections_broker,
            discovery_parameters,
        )

        old_services = services.get("old", [])

        # Create new list of checks
        new_services = _get_post_discovery_services(host_name, services, service_filters, result,
                                                    mode)
        host_config.set_autochecks(new_services)

        result.diff_text = make_object_diff(
            _make_services_audit_log_object([x.service for x in old_services]),
            _make_services_audit_log_object([x.service for x in new_services]))

    except MKTimeout:
        raise  # let general timeout through

    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        result.error_text = str(e)

    if mode != "remove":
        result.self_new_host_labels = sum(host_label_discovery_result.per_plugin.values())
        result.self_total_host_labels = len(host_label_discovery_result.labels)

    result.self_total = result.self_new + result.self_kept
    return result


def _make_services_audit_log_object(services: List[Service]) -> Set[str]:
    """The resulting object is used for building object diffs"""
    return {s.description for s in services}


def _get_post_discovery_services(
    host_name: HostName,
    services: ServicesByTransition,
    service_filters: ServiceFilters,
    result: DiscoveryResult,
    mode: str,
) -> List[ServiceWithNodes]:
    """
    The output contains a selction of services in the states "new", "old", "ignored", "vanished"
    (depending on the value of `mode`) and "clusterd_".

    Service in with the state "custom", "legacy", "active" and "manual" are currently not checked.

    Note:

        Discovered checks that are shadowed by manual checks will vanish that way.

    """
    post_discovery_services: List[ServiceWithNodes] = []
    for check_source, discovered_services_with_nodes in services.items():
        if check_source in ("custom", "legacy", "active", "manual"):
            # This is not an autocheck or ignored and currently not
            # checked. Note: Discovered checks that are shadowed by manual
            # checks will vanish that way.
            continue

        if check_source == "new":
            if mode in ("new", "fixall", "refresh"):
                new = [
                    s for s in discovered_services_with_nodes
                    if service_filters.new(host_name, s.service)
                ]
                result.self_new += len(new)
                post_discovery_services.extend(new)
            continue

        if check_source in ("old", "ignored"):
            # keep currently existing valid services in any case
            post_discovery_services.extend(discovered_services_with_nodes)
            result.self_kept += len(discovered_services_with_nodes)
            continue

        if check_source == "vanished":
            # keep item, if we are currently only looking for new services
            # otherwise fix it: remove ignored and non-longer existing services
            for entry in discovered_services_with_nodes:
                if mode in ("fixall", "remove") and service_filters.vanished(
                        host_name, entry.service):
                    result.self_removed += 1
                else:
                    post_discovery_services.append(entry)
                    result.self_kept += 1
            continue

        if check_source.startswith("clustered_"):
            # Silently keep clustered services
            post_discovery_services.extend(discovered_services_with_nodes)
            setattr(result, check_source,
                    getattr(result, check_source) + len(discovered_services_with_nodes))
            continue

        raise MKGeneralException("Unknown check source '%s'" % check_source)

    return post_discovery_services


#.
#   .--Discovery Check-----------------------------------------------------.
#   |           ____  _                   _               _                |
#   |          |  _ \(_)___  ___      ___| |__   ___  ___| | __            |
#   |          | | | | / __|/ __|    / __| '_ \ / _ \/ __| |/ /            |
#   |          | |_| | \__ \ (__ _  | (__| | | |  __/ (__|   <             |
#   |          |____/|_|___/\___(_)  \___|_| |_|\___|\___|_|\_\            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Active check for checking undiscovered services.                    |
#   '----------------------------------------------------------------------'


@cmk.base.decorator.handle_check_mk_check_result("discovery", "Check_MK Discovery")
def check_discovery(
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    *,
    # The next argument *must* remain optional for the DiscoCheckExecutor.
    #   See Also: `cmk.base.checking.do_check()`.
    fetcher_messages: Sequence[FetcherMessage] = (),
) -> Tuple[int, List[str], List[str], List[Tuple]]:

    # Note: '--cache' is set in core_cmc, nagios template or even on CL and means:
    # 1. use caches as default:
    #    - Set FileCacheFactory.maybe = True (set max_cachefile_age, else 0)
    #    - Set FileCacheFactory.use_outdated = True
    # 2. Then these settings are used to read cache file or not
    # 3. If params['inventory_check_do_scan'] = True in 'Periodic service discovery'
    #    then caching is disabled, but only for SNMP data sources:
    #    - FileCacheFactory.snmp_disabled = True
    #      -> FileCacheFactory.disabled = True
    #    For agent-based data sources we do not disable cache because of some special
    #    cases (eg. logwatch) in order to prevent stealing data (log lines etc.)

    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(host_name)
    discovery_parameters = DiscoveryParameters(
        on_error="raise",
        load_labels=True,
        save_labels=False,
        only_host_labels=False,
    )

    params = host_config.discovery_check_parameters
    if params is None:
        params = host_config.default_discovery_check_parameters()

    # In case of keepalive discovery we always have an ipaddress. When called as non keepalive
    # ipaddress is always None
    if ipaddress is None and not host_config.is_cluster:
        ipaddress = ip_lookup.lookup_ip_address(
            host_config,
            family=host_config.default_address_family,
        )

    mode = (Mode.DISCOVERY if params['inventory_check_do_scan'] else Mode.CACHED_DISCOVERY)

    nodes = sources.make_nodes(
        config_cache,
        host_config,
        ipaddress,
        mode,
        sources.make_sources(host_config, ipaddress, mode=mode),
    )
    use_caches = cmk.core_helpers.cache.FileCacheFactory.maybe
    max_cachefile_age = config.discovery_max_cachefile_age(use_caches)
    if not fetcher_messages:
        # Note: *Not* calling `fetch_all(sources)` here is probably buggy.
        #       Also See: `cmk.base.checking.do_check()`
        fetcher_messages = list(
            sources.fetch_all(
                nodes,
                max_cachefile_age=max_cachefile_age,
                host_config=host_config,
            ))

    parsed_sections_broker = ParsedSectionsBroker()
    result = sources.update_host_sections(
        parsed_sections_broker,
        nodes,
        max_cachefile_age=max_cachefile_age,
        host_config=host_config,
        fetcher_messages=fetcher_messages,
        selected_sections=NO_SELECTION,
    )

    services, host_label_discovery_result = _get_host_services(
        host_config,
        ipaddress,
        parsed_sections_broker,
        discovery_parameters,
    )

    status, infotexts, long_infotexts, perfdata, need_rediscovery = _check_service_lists(
        host_name,
        services,
        params,
    )

    if host_label_discovery_result.per_plugin:
        infotexts.append("%d new host labels" %
                         sum(host_label_discovery_result.per_plugin.values()))
        status = cmk.base.utils.worst_service_state(status,
                                                    params.get("severity_new_host_label", 1))

        if _get_rediscovery_mode(params) in ("new", "fixall", "refresh"):
            need_rediscovery = True
    else:
        infotexts.append("no new host labels")

    if need_rediscovery:
        if host_config.is_cluster and host_config.nodes:
            for nodename in host_config.nodes:
                _set_rediscovery_flag(nodename)
        else:
            _set_rediscovery_flag(host_name)
        infotexts.append(u"rediscovery scheduled")

    # Add data source information to check results
    for source, host_sections in result:
        source_state, source_output, _source_perfdata = source.summarize(host_sections)
        # Do not output informational (state = 0) things.  These information
        # are shown by the "Check_MK" service
        if source_state != 0:
            status = max(status, source_state)
            infotexts.append(u"[%s] %s" % (source.id, source_output))

    return status, infotexts, long_infotexts, perfdata


def _check_service_lists(
    host_name: HostName,
    services_by_transition: ServicesByTransition,
    params: Dict,
) -> Tuple[int, List[str], List[str], List[Tuple], bool]:

    status = 0
    infotexts = []
    long_infotexts = []
    perfdata: List[Tuple] = []
    need_rediscovery = False

    service_filters = get_service_filter_funcs(params)
    rediscovery_mode = _get_rediscovery_mode(params)

    for transition, title, params_key, default_state, service_filter in [
        ("new", "unmonitored", "severity_unmonitored", config.inventory_check_severity,
         service_filters.new),
        ("vanished", "vanished", "severity_vanished", 0, service_filters.vanished),
    ]:

        affected_check_plugin_names: Counter[CheckPluginName] = Counter()
        unfiltered = False

        for (discovered_service, _found_on_nodes) in services_by_transition.get(transition, []):
            affected_check_plugin_names[discovered_service.check_plugin_name] += 1

            if not unfiltered and service_filter(host_name, discovered_service):
                unfiltered = True

            #TODO In service_filter:we use config.service_description(...)
            # in order to finalize service_description (translation, etc.).
            # Why do we use discovered_service.description here?
            long_infotexts.append(
                u"%s: %s: %s" %
                (title, discovered_service.check_plugin_name, discovered_service.description))

        if affected_check_plugin_names:
            info = ", ".join(["%s:%d" % e for e in affected_check_plugin_names.items()])
            st = params.get(params_key, default_state)
            status = cmk.base.utils.worst_service_state(status, st)
            infotexts.append(u"%d %s services (%s)%s" % (
                sum(affected_check_plugin_names.values()),
                title,
                info,
                state_markers[st],
            ))

            if (unfiltered and
                ((transition == "new" and rediscovery_mode in ("new", "fixall", "refresh")) or
                 (transition == "vanished" and
                  rediscovery_mode in ("remove", "fixall", "refresh")))):
                need_rediscovery = True
        else:
            infotexts.append(u"no %s services found" % title)

    for (discovered_service, _found_on_nodes) in services_by_transition.get("ignored", []):
        long_infotexts.append(
            u"ignored: %s: %s" %
            (discovered_service.check_plugin_name, discovered_service.description))

    return status, infotexts, long_infotexts, perfdata, need_rediscovery


def _set_rediscovery_flag(host_name: HostName) -> None:
    def touch(filename: str) -> None:
        if not os.path.exists(filename):
            f = open(filename, "w")
            f.close()

    autodiscovery_dir = cmk.utils.paths.var_dir + '/autodiscovery'
    discovery_filename = os.path.join(autodiscovery_dir, host_name)

    if not os.path.exists(autodiscovery_dir):
        os.makedirs(autodiscovery_dir)
    touch(discovery_filename)


class DiscoveryTimeout(MKException):
    pass


def _handle_discovery_timeout(signum: int, stack_frame: Optional[FrameType]) -> NoReturn:
    raise DiscoveryTimeout()


def _set_discovery_timeout() -> None:
    signal.signal(signal.SIGALRM, _handle_discovery_timeout)
    # Add an additional 10 seconds as grace period
    signal.alarm(_marked_host_discovery_timeout + 10)


def _clear_discovery_timeout() -> None:
    signal.alarm(0)


def _get_autodiscovery_dir() -> str:
    return cmk.utils.paths.var_dir + '/autodiscovery'


def discover_marked_hosts(core: MonitoringCore) -> None:
    console.verbose("Doing discovery for all marked hosts:\n")
    autodiscovery_dir = _get_autodiscovery_dir()

    if not os.path.exists(autodiscovery_dir):
        # there is obviously nothing to do
        console.verbose("  Nothing to do. %s is missing.\n" % autodiscovery_dir)
        return

    config_cache = config.get_config_cache()

    now_ts = time.time()
    end_time_ts = now_ts + _marked_host_discovery_timeout  # don't run for more than 2 minutes
    oldest_queued = _queue_age()
    hosts = os.listdir(autodiscovery_dir)
    if not hosts:
        console.verbose("  Nothing to do. No hosts marked by discovery check.\n")

    # Fetch host state information from livestatus
    host_states = _fetch_host_states()
    activation_required = False

    try:
        _set_discovery_timeout()
        for host_name in hosts:
            host_config = config_cache.get_host_config(host_name)

            if not _discover_marked_host_exists(config_cache, host_name):
                continue

            # Only try to discover hosts with UP state
            if host_states and host_states.get(host_name) != 0:
                continue

            if _discover_marked_host(config_cache, host_config, now_ts, oldest_queued):
                activation_required = True

            if time.time() > end_time_ts:
                console.verbose(
                    "  Timeout of %d seconds reached. Lets do the remaining hosts next time." %
                    _marked_host_discovery_timeout)
                break
    except DiscoveryTimeout:
        pass
    finally:
        _clear_discovery_timeout()

    if activation_required:
        console.verbose("\nRestarting monitoring core with updated configuration...\n")
        with config.set_use_core_config(use_core_config=False):
            try:
                _config_cache.clear_all()
                config.get_config_cache().initialize()

                if config.monitoring_core == "cmc":
                    cmk.base.core.do_reload(core)
                else:
                    cmk.base.core.do_restart(core)
            finally:
                _config_cache.clear_all()
                config.get_config_cache().initialize()


def _fetch_host_states() -> Dict[HostName, HostState]:
    try:
        query = "GET hosts\nColumns: name state"
        response = livestatus.LocalConnection().query(query)
        return {k: v for row in response for k, v in [_parse_row(row)]}
    except (livestatus.MKLivestatusNotFoundError, livestatus.MKLivestatusSocketError):
        pass
    return {}


def _parse_row(row: livestatus.LivestatusRow) -> Tuple[HostName, HostState]:
    host_name, host_state = row
    if isinstance(host_name, HostName) and isinstance(host_state, HostState):
        return host_name, host_state
    raise MKGeneralException("Invalid response from livestatus: %s" % row)


def _discover_marked_host_exists(config_cache: config.ConfigCache, host_name: HostName) -> bool:
    if host_name in config_cache.all_configured_hosts():
        return True

    host_flag_path = os.path.join(_get_autodiscovery_dir(), host_name)
    try:
        os.remove(host_flag_path)
    except OSError:
        pass
    console.verbose(
        f"  Skipped. Host {host_name} does not exist in configuration. Removing mark.\n")
    return False


def _discover_marked_host(config_cache: config.ConfigCache, host_config: config.HostConfig,
                          now_ts: float, oldest_queued: float) -> bool:
    host_name = host_config.hostname
    something_changed = False

    console.verbose(f"{tty.bold}{host_name}{tty.normal}:\n")
    host_flag_path = os.path.join(_get_autodiscovery_dir(), host_name)

    params = host_config.discovery_check_parameters
    if params is None:
        console.verbose("  failed: discovery check disabled\n")
        return False

    service_filters = get_service_filter_funcs(params)

    reason = _may_rediscover(params, now_ts, oldest_queued)
    if not reason:
        result = discover_on_host(
            config_cache,
            host_config,
            _get_rediscovery_mode(params),
            use_caches=True,
            service_filters=service_filters,
        )
        if result.error_text is not None:
            if result.error_text:
                console.verbose(f"failed: {result.error_text}\n")
            else:
                # for offline hosts the error message is empty. This is to remain
                # compatible with the automation code
                console.verbose("  failed: host is offline\n")
        else:
            if result.self_new == 0 and\
               result.self_removed == 0 and\
               result.self_kept == result.self_total and\
               result.clustered_new == 0 and\
               result.clustered_vanished == 0 and\
               result.self_new_host_labels == 0:
                console.verbose("  nothing changed.\n")
            else:
                console.verbose(f"  {result.self_new} new, {result.self_removed} removed, "
                                f"{result.self_kept} kept, {result.self_total} total services "
                                f"and {result.self_new_host_labels} new host labels. "
                                f"clustered new {result.clustered_new}, clustered vanished "
                                f"{result.clustered_vanished}")

                # Note: Even if the actual mark-for-discovery flag may have been created by a cluster host,
                #       the activation decision is based on the discovery configuration of the node
                if _get_rediscovery_parameters(params)["activation"]:
                    something_changed = True

                # Enforce base code creating a new host config object after this change
                config_cache.invalidate_host_config(host_name)

                # Now ensure that the discovery service is updated right after the changes
                schedule_discovery_check(host_name)

        # delete the file even in error case, otherwise we might be causing the same error
        # every time the cron job runs
        try:
            os.remove(host_flag_path)
        except OSError:
            pass
    else:
        console.verbose(f"  skipped: {reason}\n")

    return something_changed


def _queue_age() -> float:
    autodiscovery_dir = _get_autodiscovery_dir()
    oldest = time.time()
    for filename in os.listdir(autodiscovery_dir):
        oldest = min(oldest, os.path.getmtime(autodiscovery_dir + "/" + filename))
    return oldest


def _may_rediscover(params: config.DiscoveryCheckParameters, now_ts: float,
                    oldest_queued: float) -> str:
    if "inventory_rediscovery" not in params:
        return "automatic discovery disabled for this host"

    rediscovery_parameters = _get_rediscovery_parameters(params)
    now = time.gmtime(now_ts)
    for start_hours_mins, end_hours_mins in rediscovery_parameters["excluded_time"]:
        start_time = time.struct_time(
            (now.tm_year, now.tm_mon, now.tm_mday, start_hours_mins[0], start_hours_mins[1], 0,
             now.tm_wday, now.tm_yday, now.tm_isdst))

        end_time = time.struct_time((now.tm_year, now.tm_mon, now.tm_mday, end_hours_mins[0],
                                     end_hours_mins[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst))

        if start_time <= now <= end_time:
            return "we are currently in a disallowed time of day"

    if now_ts - oldest_queued < rediscovery_parameters["group_time"]:
        return "last activation is too recent"

    return ""


#.
#   .--Host labels---------------------------------------------------------.
#   |           _   _           _     _       _          _                 |
#   |          | | | | ___  ___| |_  | | __ _| |__   ___| |___             |
#   |          | |_| |/ _ \/ __| __| | |/ _` | '_ \ / _ \ / __|            |
#   |          |  _  | (_) \__ \ |_  | | (_| | |_) |  __/ \__ \            |
#   |          |_| |_|\___/|___/\__| |_|\__,_|_.__/ \___|_|___/            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _analyse_host_labels(
    *,
    host_name: HostName,
    discovered_host_labels: DiscoveredHostLabels,
    existing_host_labels: DiscoveredHostLabels,
    discovery_parameters: DiscoveryParameters,
) -> Tuple[DiscoveredHostLabels, Counter[str]]:

    section.section_step("Analyse discovered host labels")

    old_labels_set = {x.label for x in existing_host_labels.to_list()}
    new_labels_set = {x.label for x in discovered_host_labels.to_list()}

    new_host_labels_per_plugin: Counter[str] = Counter()
    # TODO: drop the unnecessary creation of DiscoveredHostLabels objects
    return_host_labels = DiscoveredHostLabels.from_dict(existing_host_labels.to_dict())
    for label in discovered_host_labels.values():
        if label.label in old_labels_set:
            continue
        return_host_labels.add_label(label)
        new_host_labels_per_plugin[label.plugin_name] += 1

    if discovery_parameters.save_labels:
        DiscoveredHostLabelsStore(host_name).save(return_host_labels.to_dict())

    if new_labels_set - old_labels_set:
        # Some check plugins like 'df' may discover services based on host labels.
        # A rule may look like:
        # [{
        #     'value': {
        #         'ignore_fs_types': ['tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660'],
        #         'never_ignore_mountpoints': ['~.*/omd/sites/[^/]+/tmp$']
        #     },
        #     'condition': {
        #         'host_labels': {
        #             'cmk/check_mk_server': 'yes'
        #         }
        #     }
        # }]
        # In the first step '_discover_host_labels' the ruleset optimizer caches the
        # result of the evaluation of these rules. Contemporary we may find new host
        # labels which are not yet taken into account by the ruleset optimizer.
        # In the next step '_discover_services' we want to discover new services
        # based on these new host labels but we only got the cached result.
        # If we found new host labels, we have to evaluate these rules again in order
        # to find new services, eg. in 'inventory_df'. Thus we have to clear these caches.
        config.get_config_cache().ruleset_matcher.ruleset_optimizer.clear_caches()

    return return_host_labels, new_host_labels_per_plugin


def _load_existing_host_labels(
    *,
    host_name: HostName,
    discovery_parameters: DiscoveryParameters,
) -> DiscoveredHostLabels:
    # Take over old items if -I is selected
    if not discovery_parameters.load_labels:
        return DiscoveredHostLabels()

    raw_label_dict = DiscoveredHostLabelsStore(host_name).load()
    return DiscoveredHostLabels.from_dict(raw_label_dict)


def _discover_host_labels(
    *,
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    parsed_sections_broker: ParsedSectionsBroker,
    discovery_parameters: DiscoveryParameters,
) -> DiscoveredHostLabels:

    section.section_step("Discover host labels of section plugins")

    discovered_host_labels = _discover_host_labels_for_source_type(
        host_key=HostKey(host_name, ipaddress, SourceType.HOST),
        parsed_sections_broker=parsed_sections_broker,
        discovery_parameters=discovery_parameters,
    )
    discovered_host_labels += _discover_host_labels_for_source_type(
        host_key=HostKey(host_name, ipaddress, SourceType.MANAGEMENT),
        parsed_sections_broker=parsed_sections_broker,
        discovery_parameters=discovery_parameters,
    )

    return discovered_host_labels


def _discover_host_labels_for_source_type(
    *,
    host_key: sources.host_sections.HostKey,
    parsed_sections_broker: ParsedSectionsBroker,
    discovery_parameters: DiscoveryParameters,
) -> DiscoveredHostLabels:

    try:
        host_data = parsed_sections_broker[host_key]
    except KeyError:
        return DiscoveredHostLabels()

    discovered_host_labels: DiscoveredHostLabelsDict = {}
    try:
        # We do *not* process all available raw sections. Instead we see which *parsed*
        # sections would result from them, and then process those.
        parse_sections = {
            agent_based_register.get_section_plugin(rs).parsed_section_name
            for rs in host_data.sections
        }
        applicable_sections = parsed_sections_broker.determine_applicable_sections(
            parse_sections,
            host_key.source_type,
        )

        console.vverbose("Trying host label discovery with: %s\n" %
                         ", ".join(str(s.name) for s in applicable_sections))
        for section_plugin in _sort_sections_by_label_priority(applicable_sections):

            kwargs = {
                'section': parsed_sections_broker.get_parsed_section(
                    host_key, section_plugin.parsed_section_name),
            }

            host_label_params = config.get_host_label_parameters(host_key.hostname, section_plugin)
            if host_label_params is not None:
                kwargs["params"] = host_label_params

            try:
                for label in section_plugin.host_label_function(**kwargs):
                    console.vverbose(f"  {label.name}: {label.value} ({section_plugin.name})\n")
                    discovered_host_labels[label.name] = {
                        "plugin_name": str(section_plugin.name),
                        "value": label.value,
                    }
            except (KeyboardInterrupt, MKTimeout):
                raise
            except Exception as exc:
                if cmk.utils.debug.enabled() or discovery_parameters.on_error == "raise":
                    raise
                if discovery_parameters.on_error == "warn":
                    console.error("Host label discovery of '%s' failed: %s\n" %
                                  (section_plugin.name, exc))

    except KeyboardInterrupt:
        raise MKGeneralException("Interrupted by Ctrl-C.")

    return DiscoveredHostLabels.from_dict(discovered_host_labels)


# snmp_info.include sets a couple of host labels for device type but should not
# overwrite device specific ones. So we put the snmp_info section first.
def _sort_sections_by_label_priority(sections):
    return sorted(sections, key=lambda s: (s.name != SectionName("snmp_info"), s.name))


#.
#   .--Discovery-----------------------------------------------------------.
#   |              ____  _                                                 |
#   |             |  _ \(_)___  ___ _____   _____ _ __ _   _               |
#   |             | | | | / __|/ __/ _ \ \ / / _ \ '__| | | |              |
#   |             | |_| | \__ \ (_| (_) \ V /  __/ |  | |_| |              |
#   |             |____/|_|___/\___\___/ \_/ \___|_|   \__, |              |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+
#   |  Core code of actual service discovery                               |
#   '----------------------------------------------------------------------'


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


def _discover_host_labels_and_services(
    *,
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    parsed_sections_broker: ParsedSectionsBroker,
    discovery_parameters: DiscoveryParameters,
    run_only_plugin_names: Optional[Set[CheckPluginName]],
) -> Tuple[List[Service], HostLabelDiscoveryResult]:
    """Discovers host labels and services per real host or node"""

    host_labels, host_labels_per_plugin = _analyse_host_labels(
        host_name=host_name,
        discovered_host_labels=_discover_host_labels(
            host_name=host_name,
            ipaddress=ipaddress,
            parsed_sections_broker=parsed_sections_broker,
            discovery_parameters=discovery_parameters,
        ),
        existing_host_labels=_load_existing_host_labels(
            host_name=host_name,
            discovery_parameters=discovery_parameters,
        ),
        discovery_parameters=discovery_parameters,
    )

    discovered_services = [] if discovery_parameters.only_host_labels else _discover_services(
        host_name=host_name,
        ipaddress=ipaddress,
        parsed_sections_broker=parsed_sections_broker,
        discovery_parameters=discovery_parameters,
        run_only_plugin_names=run_only_plugin_names,
    )

    return discovered_services, HostLabelDiscoveryResult(
        labels=host_labels,
        per_plugin=host_labels_per_plugin,
    )


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


# Creates a table of all services that a host has or could have according
# to service discovery. The result is a tuple of services / labels, where
# the services are in a dictionary of the form
# service_transition -> List[Service]
# service_transition is the reason/state/source of the service:
#    "new"           : Check is discovered but currently not yet monitored
#    "old"           : Check is discovered and already monitored (most common)
#    "vanished"      : Check had been discovered previously, but item has vanished
#    "active"        : Check is defined via active_checks
#    "custom"        : Check is defined via custom_checks
#    "manual"        : Check is a manual Checkmk check without service discovery
#    "ignored"       : discovered or static, but disabled via ignored_services
#    "clustered_new" : New service found on a node that belongs to a cluster
#    "clustered_old" : Old service found on a node that belongs to a cluster
# This function is cluster-aware
def _get_host_services(
    host_config: config.HostConfig,
    ipaddress: Optional[HostAddress],
    parsed_sections_broker: ParsedSectionsBroker,
    discovery_parameters: DiscoveryParameters,
) -> Tuple[ServicesByTransition, HostLabelDiscoveryResult]:

    if host_config.is_cluster:
        services, host_label_discovery_result = _get_cluster_services(
            host_config,
            ipaddress,
            parsed_sections_broker,
            discovery_parameters,
        )
    else:
        services, host_label_discovery_result = _get_node_services(
            host_config,
            ipaddress,
            parsed_sections_broker,
            discovery_parameters,
        )

    # Now add manual and active service and handle ignored services
    return _merge_manual_services(host_config, services,
                                  discovery_parameters), host_label_discovery_result


# Do the actual work for a non-cluster host or node
def _get_node_services(
    host_config: config.HostConfig,
    ipaddress: Optional[HostAddress],
    parsed_sections_broker: ParsedSectionsBroker,
    discovery_parameters: DiscoveryParameters,
) -> Tuple[ServicesTable, HostLabelDiscoveryResult]:

    host_name = host_config.hostname
    services, host_label_discovery_result = _get_discovered_services(
        host_name,
        ipaddress,
        parsed_sections_broker,
        discovery_parameters,
    )

    config_cache = config.get_config_cache()
    # Identify clustered services
    for check_source, service, found_on_nodes in services.values():
        clustername = config_cache.host_of_clustered_service(host_name, service.description)
        if host_name != clustername:
            if config.service_ignored(clustername, service.check_plugin_name, service.description):
                check_source = "ignored"
            services[service.id()] = ("clustered_" + check_source, service, found_on_nodes)

    return services, host_label_discovery_result


# Part of _get_node_services that deals with discovered services
def _get_discovered_services(
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    parsed_sections_broker: ParsedSectionsBroker,
    discovery_parameters: DiscoveryParameters,
) -> Tuple[ServicesTable, HostLabelDiscoveryResult]:

    # Handle discovered services -> "new"
    discovered_services, host_label_discovery_result = _discover_host_labels_and_services(
        host_name=host_name,
        ipaddress=ipaddress,
        parsed_sections_broker=parsed_sections_broker,
        discovery_parameters=discovery_parameters,
        run_only_plugin_names=None,
    )

    # Create a dict from check_plugin_name/item to check_source/paramstring
    services: ServicesTable = {}
    for discovered_service in discovered_services:
        services.setdefault(discovered_service.id(), ("new", discovered_service, [host_name]))

    # Match with existing items -> "old" and "vanished"
    for existing_service in autochecks.parse_autochecks_file(host_name, config.service_description):
        check_source = "vanished" if existing_service.id() not in services else "old"
        services[existing_service.id()] = check_source, existing_service, [host_name]

    return services, host_label_discovery_result


# TODO: Rename or extract disabled services handling
def _merge_manual_services(
    host_config: config.HostConfig,
    services: ServicesTable,
    discovery_parameters: DiscoveryParameters,
) -> ServicesByTransition:
    """Add/replace manual and active checks and handle ignoration"""
    host_name = host_config.hostname

    # Find manual checks. These can override discovered checks -> "manual"
    manual_items = check_table.get_check_table(host_name, skip_autochecks=True)
    for service in manual_items.values():
        services[service.id()] = ('manual', service, [host_name])

    # Add custom checks -> "custom"
    for entry in host_config.custom_checks:
        services[(CheckPluginName('custom'), entry['service_description'])] = (
            'custom',
            Service(
                check_plugin_name=CheckPluginName('custom'),
                item=entry['service_description'],
                description=entry['service_description'],
                parameters=None,
            ),
            [host_name],
        )

    # Similar for 'active_checks', but here we have parameters
    for plugin_name, entries in host_config.active_checks:
        for params in entries:
            descr = config.active_check_service_description(host_name, plugin_name, params)
            services[(CheckPluginName(plugin_name), descr)] = (
                'active',
                Service(
                    check_plugin_name=CheckPluginName(plugin_name),
                    item=descr,
                    description=descr,
                    parameters=params,
                ),
                [host_name],
            )

    # Handle disabled services -> "ignored"
    for check_source, discovered_service, _found_on_nodes in services.values():
        if check_source in ["legacy", "active", "custom"]:
            # These are ignored later in get_check_preview
            # TODO: This needs to be cleaned up. The problem here is that service_description() can not
            # calculate the description of active checks and the active checks need to be put into
            # "[source]_ignored" instead of ignored.
            continue

        if config.service_ignored(host_name, discovered_service.check_plugin_name,
                                  discovered_service.description):
            services[discovered_service.id()] = ("ignored", discovered_service, [host_name])

    return _group_by_transition(services.values())


def _group_by_transition(
        transition_services: Iterable[Tuple[str, Service, List[HostName]]]) -> ServicesByTransition:
    services_by_transition: ServicesByTransition = {}
    for transition, service, found_on_nodes in transition_services:
        services_by_transition.setdefault(transition,
                                          []).append(ServiceWithNodes(service, found_on_nodes))
    return services_by_transition


def _get_cluster_services(
    host_config: config.HostConfig,
    ipaddress: Optional[str],
    parsed_sections_broker: ParsedSectionsBroker,
    discovery_parameters: DiscoveryParameters,
) -> Tuple[ServicesTable, HostLabelDiscoveryResult]:
    if not host_config.nodes:
        return {}, HostLabelDiscoveryResult(
            labels=DiscoveredHostLabels(),
            per_plugin=Counter(),
        )

    cluster_items: ServicesTable = {}
    cluster_host_labels = DiscoveredHostLabels()
    config_cache = config.get_config_cache()

    # Get services of the nodes. We are only interested in "old", "new" and "vanished"
    # From the states and parameters of these we construct the final state per service.
    for node in host_config.nodes:
        node_config = config_cache.get_host_config(node)
        services, host_label_discovery_result = _get_discovered_services(
            node,
            ip_lookup.lookup_ip_address(node_config, family=node_config.default_address_family),
            parsed_sections_broker,
            discovery_parameters,
        )
        cluster_host_labels.update(host_label_discovery_result.labels)
        for check_source, discovered_service, found_on_nodes in services.values():
            if host_config.hostname != config_cache.host_of_clustered_service(
                    node, discovered_service.description):
                continue  # not part of this host

            if discovered_service.id() not in cluster_items:
                cluster_items[discovered_service.id()] = (check_source, discovered_service,
                                                          found_on_nodes)
                continue

            first_check_source, first_discovered_service, nodes_with_service = cluster_items[
                discovered_service.id()]
            if node not in nodes_with_service:
                nodes_with_service.append(node)

            if first_check_source == "old":
                continue

            if check_source == "old":
                cluster_items[discovered_service.id()] = (check_source, discovered_service,
                                                          nodes_with_service)
                continue

            if first_check_source == "vanished" and check_source == "new":
                cluster_items[discovered_service.id()] = ("old", first_discovered_service,
                                                          nodes_with_service)
                continue

            if check_source == "vanished" and first_check_source == "new":
                cluster_items[discovered_service.id()] = ("old", discovered_service,
                                                          nodes_with_service)
                continue

            # In all other cases either both must be "new" or "vanished" -> let it be

    cluster_host_labels, cluster_labels_per_plugin = _analyse_host_labels(
        host_name=host_config.hostname,
        discovered_host_labels=cluster_host_labels,
        existing_host_labels=_load_existing_host_labels(
            host_name=host_config.hostname,
            discovery_parameters=discovery_parameters,
        ),
        discovery_parameters=discovery_parameters,
    )
    return cluster_items, HostLabelDiscoveryResult(
        labels=cluster_host_labels,
        per_plugin=cluster_labels_per_plugin,
    )


def get_check_preview(
    host_name: HostName,
    *,
    use_caches: bool,
    on_error: str,
) -> Tuple[CheckPreviewTable, DiscoveredHostLabels]:
    """Get the list of service of a host or cluster and guess the current state of
    all services if possible"""
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(host_name)

    ip_address = None if host_config.is_cluster else ip_lookup.lookup_ip_address(
        host_config,
        family=host_config.default_address_family,
    )
    discovery_parameters = DiscoveryParameters(
        on_error=on_error,
        load_labels=False,
        save_labels=False,
        only_host_labels=False,
    )

    mode = Mode.CACHED_DISCOVERY if use_caches else Mode.DISCOVERY

    nodes = sources.make_nodes(
        config_cache, host_config, ip_address, mode,
        sources.make_sources(
            host_config,
            ip_address,
            mode=mode,
            on_scan_error=on_error,
        ))
    max_cachefile_age = config.discovery_max_cachefile_age(use_caches)

    parsed_sections_broker = ParsedSectionsBroker()
    sources.update_host_sections(
        parsed_sections_broker,
        nodes,
        max_cachefile_age=max_cachefile_age,
        host_config=host_config,
        fetcher_messages=list(
            sources.fetch_all(
                nodes,
                max_cachefile_age=max_cachefile_age,
                host_config=host_config,
            )),
        selected_sections=NO_SELECTION,
    )

    grouped_services, host_label_discovery_result = _get_host_services(
        host_config,
        ip_address,
        parsed_sections_broker,
        discovery_parameters,
    )

    table: CheckPreviewTable = []
    for check_source, services_with_nodes in grouped_services.items():
        for service, found_on_nodes in services_with_nodes:
            plugin = agent_based_register.get_check_plugin(service.check_plugin_name)
            params = _preview_params(host_name, service, plugin, check_source)

            if check_source in ['legacy', 'active', 'custom']:
                exitcode = None
                output = u"WAITING - %s check, cannot be done offline" % check_source.title()
                ruleset_name: Optional[RulesetName] = None
            else:
                if plugin is None:
                    continue  # Skip not existing check silently

                ruleset_name = str(plugin.check_ruleset_name) if plugin.check_ruleset_name else None
                wrapped_params = (None if plugin.check_default_parameters is None else Parameters(
                    wrap_parameters(params)))

                _submit, _data_rx, (exitcode, output, _perfdata) = checking.get_aggregated_result(
                    parsed_sections_broker,
                    host_config,
                    ip_address,
                    service,
                    plugin,
                    lambda p=wrapped_params: p,  # type: ignore[misc]  # "type of lambda"
                )

            # Service discovery never uses the perfdata in the check table. That entry
            # is constantly discarded, yet passed around(back and forth) as part of the
            # discovery result in the request elements. Some perfdata VALUES are not parsable
            # by ast.literal_eval such as "inf" it lead to ValueErrors. Thus keep perfdata empty
            perfdata: List[MetricTuple] = []
            table.append((
                _preview_check_source(host_name, service, check_source),
                str(service.check_plugin_name),
                ruleset_name,
                service.item,
                service.parameters,
                params,
                service.description,
                exitcode,
                output,
                perfdata,
                service.service_labels.to_dict(),
                found_on_nodes,
            ))

    return table, host_label_discovery_result.labels


def _preview_check_source(
    host_name: HostName,
    service: Service,
    check_source: str,
) -> str:
    if (check_source in ["legacy", "active", "custom"] and
            config.service_ignored(host_name, None, service.description)):
        return "%s_ignored" % check_source
    return check_source


def _preview_params(
    host_name: HostName,
    service: Service,
    plugin: Optional[checking_classes.CheckPlugin],
    check_source: str,
) -> Optional[LegacyCheckParameters]:
    params: Optional[LegacyCheckParameters] = None

    if check_source not in ['legacy', 'active', 'custom']:
        if plugin is None:
            return params
        params = service.parameters
        if check_source != 'manual':
            params = config.compute_check_parameters(
                host_name,
                service.check_plugin_name,
                service.item,
                params,
            )

    if check_source == "active":
        params = service.parameters

    if isinstance(params, config.TimespecificParamList):
        params = {
            "tp_computed_params": {
                "params": checking.time_resolved_check_parameters(params),
                "computed_at": time.time(),
            }
        }

    return params
