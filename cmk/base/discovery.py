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
    NoReturn,
    Optional,
    Pattern,
    Set,
    Tuple,
    Union,
    NamedTuple,
)

from six import ensure_binary

import livestatus

from cmk.utils.check_utils import (
    ensure_management_name,
    is_management_name,
    maincheckify,
    unwrap_parameters,
    wrap_parameters,
)
import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.misc
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKException, MKGeneralException, MKTimeout
from cmk.utils.labels import DiscoveredHostLabelsStore
from cmk.utils.log import console
from cmk.utils.regex import regex
from cmk.utils.type_defs import (
    CheckPluginName,
    CheckPluginNameStr,
    HostAddress,
    HostName,
    HostState,
    Item,
    Metric,
    ParsedSectionName,
    RulesetName,
    SourceType,
)

import cmk.base.autochecks as autochecks
import cmk.base.check_api_utils as check_api_utils
import cmk.base.check_table as check_table
import cmk.base.check_utils
import cmk.base.checking as checking
import cmk.base.config as config
import cmk.base.core
import cmk.base.crash_reporting
import cmk.base.data_sources as data_sources
import cmk.base.decorator
import cmk.base.ip_lookup as ip_lookup
import cmk.base.section as section
import cmk.base.utils
from cmk.base.api.agent_based import checking_types
from cmk.base.api.agent_based.register.check_plugins_legacy import (
    resolve_legacy_name,)
from cmk.base.caching import config_cache as _config_cache
from cmk.base.check_utils import (
    FinalSectionContent,
    LegacyCheckParameters,
    Service,
)
from cmk.base.core_config import MonitoringCore
from cmk.base.data_sources.host_sections import HostKey, MultiHostSections
from cmk.base.discovered_labels import DiscoveredHostLabels, HostLabel

# Run the discovery queued by check_discovery() - if any
_marked_host_discovery_timeout = 120

ServicesTable = Dict[Tuple[CheckPluginNameStr, check_table.Item], Tuple[str, Service]]
CheckPreviewEntry = Tuple[str, CheckPluginNameStr, Optional[RulesetName], check_table.Item,
                          LegacyCheckParameters, LegacyCheckParameters, str, Optional[int], str,
                          List[Metric], Dict[str, str]]
CheckPreviewTable = List[CheckPreviewEntry]
DiscoveryEntry = Union[check_api_utils.Service, DiscoveredHostLabels, HostLabel,
                       Tuple[Item, LegacyCheckParameters]]
DiscoveryResult = List[DiscoveryEntry]
DiscoveryFunction = Callable[[FinalSectionContent], DiscoveryResult]
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
def schedule_discovery_check(hostname: HostName) -> None:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(cmk.utils.paths.livestatus_unix_socket)
        now = int(time.time())
        if 'cmk_inventory' in config.use_new_descriptions_for:
            command = "SCHEDULE_FORCED_SVC_CHECK;%s;Check_MK Discovery;%d" % (hostname, now)
        else:
            # TODO: Remove this old name handling one day
            command = "SCHEDULE_FORCED_SVC_CHECK;%s;Check_MK inventory;%d" % (hostname, now)

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

    return lambda hostname, service: _filter_service_by_patterns(hostname, service, whitelist,
                                                                 blacklist)


def _filter_service_by_patterns(
    hostname: HostName,
    service: Service,
    whitelist: Pattern[str],
    blacklist: Pattern[str],
) -> bool:
    #TODO Call sites: Why do we not use discovered_service.description;
    # Is discovered_service.description already finalized as
    # in config.service_description?
    # (mo): we should indeed make sure that is the case, and use it
    check_plugin_name = CheckPluginName(maincheckify(service.check_plugin_name))
    description = config.service_description(hostname, check_plugin_name, service.item)
    return whitelist.match(description) is not None and blacklist.match(description) is None


def _accept_all_services(_hostname: HostName, _service: Service) -> bool:
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
def do_discovery(arg_hostnames: Set[HostName], check_plugin_names: Optional[Set[CheckPluginName]],
                 arg_only_new: bool) -> None:
    config_cache = config.get_config_cache()
    use_caches = not arg_hostnames or data_sources.ABCDataSource.get_may_use_cache_file()
    on_error = "raise" if cmk.utils.debug.enabled() else "warn"

    host_names = _preprocess_hostnames(arg_hostnames, config_cache)

    # Now loop through all hosts
    for hostname in sorted(host_names):
        host_config = config_cache.get_host_config(hostname)
        section.section_begin(hostname)
        try:
            ipaddress = ip_lookup.lookup_ip_address(hostname)

            # Usually we disable SNMP scan if cmk -I is used without a list of
            # explicit hosts. But for host that have never been service-discovered
            # yet (do not have autochecks), we enable SNMP scan.
            do_snmp_scan = not use_caches or not autochecks.has_autochecks(hostname)

            # If check plugins are specified via command line,
            # see which raw sections we may need
            selected_raw_sections = (None if check_plugin_names is None else
                                     config.get_relevant_raw_sections(
                                         check_plugin_names=check_plugin_names))

            multi_host_sections = data_sources.make_host_sections(
                host_config,
                ipaddress,
                _get_sources_for_discovery(
                    host_config,
                    ipaddress,
                    do_snmp_scan=do_snmp_scan,
                    on_error=on_error,
                    selected_raw_sections=selected_raw_sections,
                ),
                max_cachefile_age=config.discovery_max_cachefile_age(use_caches),
            )

            _do_discovery_for(hostname, ipaddress, multi_host_sections, check_plugin_names,
                              arg_only_new, on_error)

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            section.section_error("%s" % e)
        finally:
            cmk.utils.cleanup.cleanup_globals()


def _preprocess_hostnames(arg_host_names: Set[HostName],
                          config_cache: config.ConfigCache) -> Set[HostName]:
    """Default to all hosts and expand cluster names to their nodes"""
    if not arg_host_names:
        console.verbose("Discovering services on all hosts\n")
        arg_host_names = config_cache.all_active_realhosts()
    else:
        console.verbose("Discovering services on: %s\n" % ", ".join(sorted(arg_host_names)))

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
    hostname: HostName,
    ipaddress: Optional[HostAddress],
    multi_host_sections: MultiHostSections,
    check_plugin_names: Optional[Set[CheckPluginName]],
    only_new: bool,
    on_error: str,
) -> None:
    discovered_services = _discover_services(
        hostname,
        ipaddress,
        multi_host_sections,
        on_error=on_error,
        check_plugin_whitelist=check_plugin_names,
    )

    # There are three ways of how to merge existing and new discovered checks:
    # 1. -II without --checks=
    #        check_plugin_names is empty, only_new is False
    #    --> complete drop old services, only use new ones
    # 2. -II with --checks=
    #    --> drop old services of that types
    #        check_plugin_names is not empty, only_new is False
    # 3. -I
    #    --> just add new services
    #        only_new is True

    if not check_plugin_names and not only_new:
        existing_services: List[Service] = []
    else:
        existing_services = autochecks.parse_autochecks_file(hostname, config.service_description)

    new_services: List[Service] = []
    # Take over old items if -I is selected or if -II is selected with
    # --checks= and the check type is not one of the listed ones
    for existing_service in existing_services:
        service_plugin_name = CheckPluginName(maincheckify(existing_service.check_plugin_name))
        if only_new or (check_plugin_names and service_plugin_name not in check_plugin_names):
            new_services.append(existing_service)

    services_per_plugin: Counter[check_table.CheckPluginNameStr] = Counter()
    for discovered_service in discovered_services:
        if discovered_service not in new_services:
            new_services.append(discovered_service)
            services_per_plugin[discovered_service.check_plugin_name] += 1

    autochecks.save_autochecks_file(hostname, new_services)

    section.section_step("Executing host label discovery")
    discovered_host_labels = _discover_host_labels(
        HostKey(hostname, ipaddress, SourceType.HOST),
        multi_host_sections,
        on_error=on_error,
    )
    discovered_host_labels += _discover_host_labels(
        HostKey(hostname, ipaddress, SourceType.MANAGEMENT),
        multi_host_sections,
        on_error=on_error,
    )
    new_host_labels, host_labels_per_plugin = \
        _perform_host_label_discovery(hostname, discovered_host_labels, only_new)
    DiscoveredHostLabelsStore(hostname).save(new_host_labels.to_dict())

    messages = []

    if services_per_plugin:
        for check_plugin_name, count in sorted(services_per_plugin.items()):
            console.verbose("%s%3d%s %s\n" %
                            (tty.green + tty.bold, count, tty.normal, check_plugin_name))
        messages.append("Found %d services" % sum(services_per_plugin.values()))
    else:
        messages.append("Found no%s services" % (only_new and " new" or ""))

    if host_labels_per_plugin:
        messages.append("%d host labels" % sum(host_labels_per_plugin.values()))
    else:
        messages.append("no%s host labels" % (only_new and " new" or ""))

    section.section_success(", ".join(messages))


def _perform_host_label_discovery(
        hostname: HostName, discovered_host_labels: DiscoveredHostLabels,
        only_new: bool) -> Tuple[DiscoveredHostLabels, Counter[check_table.CheckPluginNameStr]]:

    # Take over old items if -I is selected
    if only_new:
        return_host_labels = DiscoveredHostLabels.from_dict(
            DiscoveredHostLabelsStore(hostname).load())
    else:
        return_host_labels = DiscoveredHostLabels()

    new_host_labels_per_plugin: Counter[check_table.CheckPluginNameStr] = Counter()
    for discovered_label in discovered_host_labels.values():
        if discovered_label.name in return_host_labels:
            continue
        return_host_labels.add_label(discovered_label)
        new_host_labels_per_plugin[discovered_label.plugin_name] += 1

    return return_host_labels, new_host_labels_per_plugin


# determine changed services on host.
# param mode: can be one of "new", "remove", "fixall", "refresh"
# param do_snmp_scan: if True, a snmp host will be scanned, otherwise uses only the check types
#                     previously discovereda
# param servic_filter: if a filter is set, it controls whether items are touched by the discovery.
#                       if it returns False for a new item it will not be added, if it returns
#                       False for a vanished item, that item is kept
def discover_on_host(
    config_cache: config.ConfigCache,
    host_config: config.HostConfig,
    mode: str,
    do_snmp_scan: bool,
    use_caches: bool,
    service_filters: ServiceFilters,
    on_error: str = "ignore",
) -> Tuple[Dict[str, int], Optional[str]]:

    console.verbose("  Doing discovery with mode '%s'...\n" % mode)

    hostname = host_config.hostname
    counts = _empty_counts()

    if hostname not in config_cache.all_active_hosts():
        return counts, ""

    err = None
    discovered_host_labels = DiscoveredHostLabels()

    try:
        # in "refresh" mode we first need to remove all previously discovered
        # checks of the host, so that _get_host_services() does show us the
        # new discovered check parameters.
        if mode == "refresh":
            counts["self_removed"] += host_config.remove_autochecks()  # this is cluster-aware!

        if host_config.is_cluster:
            ipaddress = None
        else:
            ipaddress = ip_lookup.lookup_ip_address(hostname)

        multi_host_sections = data_sources.make_host_sections(
            host_config,
            ipaddress,
            _get_sources_for_discovery(
                host_config,
                ipaddress,
                do_snmp_scan=do_snmp_scan,
                on_error=on_error,
                for_check_discovery=True,
            ),
            max_cachefile_age=config.discovery_max_cachefile_age(use_caches),
        )

        # Compute current state of new and existing checks
        services, discovered_host_labels = _get_host_services(
            host_config,
            ipaddress,
            multi_host_sections,
            on_error=on_error,
        )

        # Create new list of checks
        new_services = _get_new_services(hostname, services, service_filters, counts, mode)
        host_config.set_autochecks(new_services)

    except MKTimeout:
        raise  # let general timeout through

    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        err = str(e)

    if mode != "remove":
        new_host_labels, host_labels_per_plugin = \
            _perform_host_label_discovery(hostname, discovered_host_labels, only_new=True)
        DiscoveredHostLabelsStore(hostname).save(new_host_labels.to_dict())
        counts["self_new_host_labels"] = sum(host_labels_per_plugin.values())
        counts["self_total_host_labels"] = len(new_host_labels)

    counts["self_total"] = counts["self_new"] + counts["self_kept"]
    return counts, err


def _empty_counts() -> Dict[str, int]:
    return {
        "self_new": 0,
        "self_removed": 0,
        "self_kept": 0,
        "self_total": 0,
        "self_new_host_labels": 0,
        "self_total_host_labels": 0,
        "clustered_new": 0,
        "clustered_old": 0,
        "clustered_vanished": 0,
    }


def _get_new_services(
    hostname: HostName,
    services: ServicesTable,
    service_filters: ServiceFilters,
    counts: Dict,
    mode: str,
) -> List[Service]:

    new_services: List[Service] = []
    for check_source, discovered_service in services.values():
        if check_source in ("custom", "legacy", "active", "manual"):
            # This is not an autocheck or ignored and currently not
            # checked. Note: Discovered checks that are shadowed by manual
            # checks will vanish that way.
            continue

        if check_source == "new":
            if mode in ("new", "fixall", "refresh") and service_filters.new(
                    hostname, discovered_service):
                counts["self_new"] += 1
                new_services.append(discovered_service)

        elif check_source in ("old", "ignored"):
            # keep currently existing valid services in any case
            new_services.append(discovered_service)
            counts["self_kept"] += 1

        elif check_source == "vanished":
            # keep item, if we are currently only looking for new services
            # otherwise fix it: remove ignored and non-longer existing services
            if mode in ("fixall", "remove") and service_filters.vanished(
                    hostname, discovered_service):
                counts["self_removed"] += 1
            else:
                new_services.append(discovered_service)
                counts["self_kept"] += 1

        elif check_source.startswith("clustered_"):
            # Silently keep clustered services
            counts[check_source] += 1
            new_services.append(discovered_service)

        else:
            raise MKGeneralException("Unknown check source '%s'" % check_source)
    return new_services


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
    hostname: HostName,
    ipaddress: Optional[HostAddress],
) -> Tuple[int, List[str], List[str], List[Tuple]]:
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    params = host_config.discovery_check_parameters
    if params is None:
        params = host_config.default_discovery_check_parameters()

    # In case of keepalive discovery we always have an ipaddress. When called as non keepalive
    # ipaddress is always None
    if ipaddress is None and not host_config.is_cluster:
        ipaddress = ip_lookup.lookup_ip_address(hostname)

    sources = _get_sources_for_discovery(
        host_config,
        ipaddress,
        do_snmp_scan=params["inventory_check_do_scan"],
        on_error="raise",
        for_check_discovery=True,
    )
    use_caches = data_sources.ABCDataSource.get_may_use_cache_file()
    multi_host_sections = data_sources.make_host_sections(
        host_config,
        ipaddress,
        sources,
        max_cachefile_age=config.discovery_max_cachefile_age(use_caches),
    )

    services, discovered_host_labels = _get_host_services(
        host_config,
        ipaddress,
        multi_host_sections,
        on_error="raise",
    )

    status, infotexts, long_infotexts, perfdata, need_rediscovery = _check_service_table(
        hostname, services, params)

    _new_host_labels, host_labels_per_plugin = _perform_host_label_discovery(
        hostname,
        discovered_host_labels,
        only_new=True,
    )

    if host_labels_per_plugin:
        infotexts.append("%d new host labels" % sum(host_labels_per_plugin.values()))
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
            _set_rediscovery_flag(hostname)
        infotexts.append(u"rediscovery scheduled")

    # Add data source information to check results
    for source in sources:
        source_state, source_output, _source_perfdata = source.get_summary_result_for_discovery()
        # Do not output informational (state = 0) things. These information are shown by the "Check_MK" service
        if source_state != 0:
            status = max(status, source_state)
            infotexts.append(u"[%s] %s" % (source.id(), source_output))

    return status, infotexts, long_infotexts, perfdata


def _check_service_table(
    hostname: HostName,
    services: ServicesTable,
    params: Dict,
) -> Tuple[int, List[str], List[str], List[Tuple], bool]:

    status = 0
    infotexts = []
    long_infotexts = []
    perfdata: List[Tuple] = []
    need_rediscovery = False

    service_filters = get_service_filter_funcs(params)
    rediscovery_mode = _get_rediscovery_mode(params)

    for check_state, title, params_key, default_state, service_filter in [
        ("new", "unmonitored", "severity_unmonitored", config.inventory_check_severity,
         service_filters.new),
        ("vanished", "vanished", "severity_vanished", 0, service_filters.vanished),
    ]:

        affected_check_plugin_names: Dict[str, int] = {}
        count = 0
        unfiltered = False

        for check_source, discovered_service in services.values():
            if check_source == check_state:
                count += 1
                affected_check_plugin_names.setdefault(discovered_service.check_plugin_name, 0)
                affected_check_plugin_names[discovered_service.check_plugin_name] += 1

                if not unfiltered and service_filter(hostname, discovered_service):
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
            infotexts.append(u"%d %s services (%s)%s" %
                             (count, title, info, check_api_utils.state_markers[st]))

            if (unfiltered and
                ((check_state == "new" and rediscovery_mode in ("new", "fixall", "refresh")) or
                 (check_state == "vanished" and
                  rediscovery_mode in ("remove", "fixall", "refresh")))):
                need_rediscovery = True
        else:
            infotexts.append(u"no %s services found" % title)

    for check_source, discovered_service in services.values():
        if check_source == "ignored":
            long_infotexts.append(
                u"ignored: %s: %s" %
                (discovered_service.check_plugin_name, discovered_service.description))

    return status, infotexts, long_infotexts, perfdata, need_rediscovery


def _set_rediscovery_flag(hostname: HostName) -> None:
    def touch(filename: str) -> None:
        if not os.path.exists(filename):
            f = open(filename, "w")
            f.close()

    autodiscovery_dir = cmk.utils.paths.var_dir + '/autodiscovery'
    discovery_filename = os.path.join(autodiscovery_dir, hostname)

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
        for hostname in hosts:
            host_config = config_cache.get_host_config(hostname)

            if not _discover_marked_host_exists(config_cache, hostname):
                continue

            # Only try to discover hosts with UP state
            if host_states and host_states.get(hostname) != 0:
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
    hostname, hoststate = row
    if isinstance(hostname, HostName) and isinstance(hoststate, HostState):
        return hostname, hoststate
    raise MKGeneralException("Invalid response from livestatus: %s" % row)


def _discover_marked_host_exists(config_cache: config.ConfigCache, hostname: HostName) -> bool:
    if hostname in config_cache.all_configured_hosts():
        return True

    host_flag_path = os.path.join(_get_autodiscovery_dir(), hostname)
    try:
        os.remove(host_flag_path)
    except OSError:
        pass
    console.verbose("  Skipped. Host %s does not exist in configuration. Removing mark.\n" %
                    hostname)
    return False


def _discover_marked_host(config_cache: config.ConfigCache, host_config: config.HostConfig,
                          now_ts: float, oldest_queued: float) -> bool:
    hostname = host_config.hostname
    something_changed = False

    console.verbose("%s%s%s:\n" % (tty.bold, hostname, tty.normal))
    host_flag_path = os.path.join(_get_autodiscovery_dir(), hostname)

    params = host_config.discovery_check_parameters
    if params is None:
        console.verbose("  failed: discovery check disabled\n")
        return False

    service_filters = get_service_filter_funcs(params)

    why_not = _may_rediscover(params, now_ts, oldest_queued)
    if not why_not:
        result, error = discover_on_host(
            config_cache,
            host_config,
            _get_rediscovery_mode(params),
            do_snmp_scan=params["inventory_check_do_scan"],
            use_caches=True,
            service_filters=service_filters,
        )
        if error is not None:
            if error:
                console.verbose("failed: %s\n" % error)
            else:
                # for offline hosts the error message is empty. This is to remain
                # compatible with the automation code
                console.verbose("  failed: host is offline\n")
        else:
            if result["self_new"] == 0 and\
               result["self_removed"] == 0 and\
               result["self_kept"] == result["self_total"] and\
               result["clustered_new"] == 0 and\
               result["clustered_vanished"] == 0 and\
               result["self_new_host_labels"] == 0:
                console.verbose("  nothing changed.\n")
            else:
                console.verbose(
                    "  %(self_new)s new, %(self_removed)s removed, "
                    "%(self_kept)s kept, %(self_total)s total services "
                    "and %(self_new_host_labels)s new host labels. "
                    "clustered new %(clustered_new)s, clustered vanished %(clustered_vanished)s" %
                    result)

                # Note: Even if the actual mark-for-discovery flag may have been created by a cluster host,
                #       the activation decision is based on the discovery configuration of the node
                if _get_rediscovery_parameters(params)["activation"]:
                    something_changed = True

                # Enforce base code creating a new host config object after this change
                config_cache.invalidate_host_config(hostname)

                # Now ensure that the discovery service is updated right after the changes
                schedule_discovery_check(hostname)

        # delete the file even in error case, otherwise we might be causing the same error
        # every time the cron job runs
        try:
            os.remove(host_flag_path)
        except OSError:
            pass
    else:
        console.verbose("  skipped: %s\n" % why_not)

    return something_changed


def _queue_age() -> float:
    autodiscovery_dir = _get_autodiscovery_dir()
    oldest = time.time()
    for filename in os.listdir(autodiscovery_dir):
        oldest = min(oldest, os.path.getmtime(autodiscovery_dir + "/" + filename))
    return oldest


def _may_rediscover(params: config.DiscoveryCheckParameters, now_ts: float,
                    oldest_queued: float) -> Optional[str]:
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

    return None


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


def _discover_host_labels(
    host_key: data_sources.host_sections.HostKey,
    multi_host_sections: MultiHostSections,
    on_error: str,
) -> DiscoveredHostLabels:
    discovered_host_labels = DiscoveredHostLabels()

    try:
        host_data = multi_host_sections[host_key]
    except KeyError:
        return discovered_host_labels

    try:
        # We do *not* process all available raw sections. Instead we see which *parsed*
        # sections would result from them, and then process those.
        section_plugins = (config.get_registered_section_plugin(rs) for rs in host_data.sections)
        parsed_sections = {p.parsed_section_name for p in section_plugins if p is not None}

        console.vverbose("Trying host label discovery with: %s\n" %
                         ", ".join(str(p) for p in parsed_sections))
        for parsed_section_name in sorted(parsed_sections):
            try:
                plugin = config.get_parsed_section_creator(parsed_section_name, host_data.sections)
                parsed = multi_host_sections.get_parsed_section(host_key, parsed_section_name)
                if plugin is None or parsed is None:
                    continue
                for label in plugin.host_label_function(parsed):
                    label.plugin_name = str(plugin.name)
                    discovered_host_labels.add_label(label)
            except (KeyboardInterrupt, MKTimeout):
                raise
            except Exception as exc:
                if cmk.utils.debug.enabled() or on_error == "raise":
                    raise
                if on_error == "warn":
                    console.error("Host label discovery of '%s' failed: %s\n" %
                                  (parsed_section_name, exc))

    except KeyboardInterrupt:
        raise MKGeneralException("Interrupted by Ctrl-C.")

    return discovered_host_labels


def _find_candidates(mhs: MultiHostSections) -> Set[CheckPluginName]:
    """Return names of check plugins that this multi_host_section may
    contain data for.

    Given this mutli_host_section, there is no point in trying to discover
    any check plugins not returned by this function.  This does not
    address the question wether or not the returned check plugins will
    discover something.

    We have to consider both the host, and the management board as source
    type. Note that the determination of the plugin names is not quite
    symmetric: For the host, we filter out all management plugins,
    for the management board we create management variants from all
    plugins that are not allready designed for management boards.

    """

    return {
        # *filter out* all names of management only check plugins
        n
        for n in _find_candidates_by_source_type(mhs, SourceType.HOST)
        if not is_management_name(n)
    } | {
        # *create* all management only names of the plugins
        ensure_management_name(n)
        for n in _find_candidates_by_source_type(mhs, SourceType.MANAGEMENT)
    }


def _find_candidates_by_source_type(
    mhs: MultiHostSections,
    source_type: SourceType,
) -> Set[CheckPluginName]:
    raw_section_names = {
        name for node_key, node_data in mhs.items() if node_key.source_type == source_type
        for name in node_data.sections
    }

    raw_sections = [(name, config.get_registered_section_plugin(name)) for name in raw_section_names
                   ]

    parsed_section_names = {
        ParsedSectionName(str(name)) if section is None else section.parsed_section_name
        for name, section in raw_sections
    }

    return {
        plugin.name
        for plugin in config.registered_check_plugins.values()
        if any(section in parsed_section_names for section in plugin.sections)
    }


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
    hostname: HostName,
    ipaddress: Optional[HostAddress],
    multi_host_sections: MultiHostSections,
    on_error: str,
    check_plugin_whitelist: Optional[Set[CheckPluginName]],
) -> List[Service]:
    # Set host name for host_name()-function (part of the Check API)
    # (used e.g. by ps-discovery)
    check_api_utils.set_hostname(hostname)

    # find out which plugins we need to discover
    plugin_candidates = _find_candidates(multi_host_sections)
    if check_plugin_whitelist is not None:
        plugin_candidates = plugin_candidates.intersection(check_plugin_whitelist)
    section.section_step("Executing discovery plugins (%d)" % len(plugin_candidates))
    console.vverbose("  Trying discovery with: %s\n" % ", ".join(str(n) for n in plugin_candidates))

    service_table: cmk.base.check_utils.CheckTable = {}
    try:
        for check_plugin_name in sorted(plugin_candidates):
            try:
                service_table.update({
                    service.id(): service for service in _execute_discovery(
                        multi_host_sections, hostname, ipaddress, check_plugin_name, on_error)
                })
            except (KeyboardInterrupt, MKTimeout):
                raise
            except Exception as e:
                if on_error == "raise":
                    raise
                if on_error == "warn":
                    console.error("Discovery of '%s' failed: %s\n" % (check_plugin_name, e))

        check_table_dedup = check_table.remove_duplicate_checks(service_table)
        return list(check_table_dedup.values())

    except KeyboardInterrupt:
        raise MKGeneralException("Interrupted by Ctrl-C.")


def _get_sources_for_discovery(
    host_config: config.HostConfig,
    ipaddress: Optional[HostAddress],
    *,
    do_snmp_scan: bool,
    on_error: str,
    for_check_discovery: bool = False,
    selected_raw_sections: Optional[config.SelectedRawSections] = None,
) -> data_sources.DataSources:
    sources = data_sources.make_sources(
        host_config,
        ipaddress,
        selected_raw_sections=selected_raw_sections,
    )
    for source in sources:
        if isinstance(source, data_sources.snmp.SNMPDataSource):
            source.set_on_error(on_error)
            source.set_do_snmp_scan(do_snmp_scan)
            source.set_use_snmpwalk_cache(False)
            source.set_ignore_check_interval(True)

            # During discovery, the snmp datasource can never fully rely on the locally cached data,
            # since the available oid trees depend on the current running checks
            # We can not disable the data_source_cache per default when caching is set
            # since this would affect the WATO service discovery page.
            if for_check_discovery and source.get_may_use_cache_file():
                data_sources.snmp.SNMPDataSource.disable_data_source_cache()

    return sources


def _execute_discovery(
    multi_host_sections: MultiHostSections,
    hostname: HostName,
    ipaddress: Optional[HostAddress],
    check_plugin_name: CheckPluginName,
    on_error: str,
) -> Iterator[Service]:
    # Skip this check type if is ignored for that host
    if config.service_ignored(hostname, check_plugin_name, None):
        console.vverbose("  Skip ignored check plugin name '%s'\n" % check_plugin_name)
        return

    check_plugin = config.registered_check_plugins.get(check_plugin_name)
    if check_plugin is None:
        console.warning("  Missing check plugin: '%s'\n" % check_plugin_name)
        return

    host_key = HostKey(
        hostname,
        ipaddress,
        SourceType.MANAGEMENT if is_management_name(check_plugin.name) else SourceType.HOST,
    )

    try:
        kwargs = multi_host_sections.get_section_kwargs(host_key, check_plugin.sections)
    except Exception as exc:
        if cmk.utils.debug.enabled() or on_error == "raise":
            raise
        if on_error == "warn":
            console.warning("  Exception while parsing agent section: %s\n" % exc)
        return
    if not kwargs:
        return

    disco_params = config.get_discovery_parameters(hostname, check_plugin)
    if disco_params is not None:
        kwargs["params"] = disco_params

    try:
        plugins_services = check_plugin.discovery_function(**kwargs)
        yield from _enriched_discovered_services(hostname, check_plugin.name, plugins_services)
    except Exception as e:
        if on_error == "warn":
            console.warning("  Exception in discovery function of check plugin '%s': %s" %
                            (check_plugin.name, e))
        elif on_error == "raise":
            raise


def _enriched_discovered_services(
    hostname: HostName,
    check_plugin_name: CheckPluginName,
    plugins_services: Iterable[checking_types.Service],
) -> Generator[Service, None, None]:
    for service in plugins_services:
        description = config.service_description(hostname, check_plugin_name, service.item)
        # make sanity check
        if len(description) == 0:
            console.error("%s: Check %s returned empty service description - ignoring it.\n" %
                          (hostname, check_plugin_name))
            continue

        yield Service(
            check_plugin_name=resolve_legacy_name(check_plugin_name),
            item=service.item,
            description=description,
            parameters=unwrap_parameters(service.parameters),
            service_labels=service.labels,
        )


# Creates a table of all services that a host has or could have according
# to service discovery. The result is a dictionary of the form
# (check_plugin_name, item) -> (check_source, paramstring)
# check_source is the reason/state/source of the service:
#    "new"           : Check is discovered but currently not yet monitored
#    "old"           : Check is discovered and already monitored (most common)
#    "vanished"      : Check had been discovered previously, but item has vanished
#    "active"        : Check is defined via active_checks
#    "custom"        : Check is defined via custom_checks
#    "manual"        : Check is a manual Check_MK check without service discovery
#    "ignored"       : discovered or static, but disabled via ignored_services
#    "clustered_new" : New service found on a node that belongs to a cluster
#    "clustered_old" : Old service found on a node that belongs to a cluster
# This function is cluster-aware
def _get_host_services(
    host_config: config.HostConfig,
    ipaddress: Optional[HostAddress],
    multi_host_sections: MultiHostSections,
    on_error: str,
) -> Tuple[ServicesTable, DiscoveredHostLabels]:
    if host_config.is_cluster:
        return _get_cluster_services(host_config, ipaddress, multi_host_sections, on_error)

    return _get_node_services(host_config, ipaddress, multi_host_sections, on_error)


# Do the actual work for a non-cluster host or node
def _get_node_services(
    host_config: config.HostConfig,
    ipaddress: Optional[HostAddress],
    multi_host_sections: MultiHostSections,
    on_error: str,
) -> Tuple[ServicesTable, DiscoveredHostLabels]:
    hostname = host_config.hostname
    services, discovered_host_labels = _get_discovered_services(hostname, ipaddress,
                                                                multi_host_sections, on_error)

    config_cache = config.get_config_cache()
    # Identify clustered services
    for check_source, service in services.values():
        clustername = config_cache.host_of_clustered_service(hostname, service.description)
        if hostname != clustername:
            # TODO(mo): centralize maincheckify: CMK-4295
            service_check_plugin_name = CheckPluginName(maincheckify(service.check_plugin_name))
            if config.service_ignored(clustername, service_check_plugin_name, service.description):
                check_source = "ignored"
            services[(service.check_plugin_name, service.item)] = ("clustered_" + check_source,
                                                                   service)

    return _merge_manual_services(host_config, services, on_error), discovered_host_labels


# Part of _get_node_services that deals with discovered services
def _get_discovered_services(
    hostname: HostName,
    ipaddress: Optional[HostAddress],
    multi_host_sections: MultiHostSections,
    on_error: str,
) -> Tuple[ServicesTable, DiscoveredHostLabels]:
    # Create a dict from check_plugin_name/item to check_source/paramstring
    services: ServicesTable = {}

    # Handle discovered services -> "new"
    discovered_services = _discover_services(
        hostname,
        ipaddress,
        multi_host_sections,
        on_error,
        check_plugin_whitelist=None,
    )
    for discovered_service in discovered_services:
        services.setdefault((discovered_service.check_plugin_name, discovered_service.item),
                            ("new", discovered_service))

    # Match with existing items -> "old" and "vanished"
    for existing_service in autochecks.parse_autochecks_file(hostname, config.service_description):
        table_id = existing_service.check_plugin_name, existing_service.item
        check_source = "vanished" if table_id not in services else "old"
        services[table_id] = check_source, existing_service

    section.section_step("Executing host label discovery")
    discovered_host_labels = _discover_host_labels(
        HostKey(hostname, ipaddress, SourceType.HOST),
        multi_host_sections,
        on_error,
    )
    discovered_host_labels += _discover_host_labels(
        HostKey(hostname, ipaddress, SourceType.MANAGEMENT),
        multi_host_sections,
        on_error,
    )

    return services, discovered_host_labels


# TODO: Rename or extract disabled services handling
def _merge_manual_services(host_config: config.HostConfig, services: ServicesTable,
                           on_error: str) -> ServicesTable:
    """Add/replace manual and active checks and handle ignoration"""
    hostname = host_config.hostname

    # Find manual checks. These can override discovered checks -> "manual"
    manual_items = check_table.get_check_table(hostname, skip_autochecks=True)
    for service in manual_items.values():
        services[(service.check_plugin_name, service.item)] = (
            'manual',
            Service(
                check_plugin_name=service.check_plugin_name,
                item=service.item,
                description=service.description,
                parameters=service.parameters,
            ),
        )

    # Add custom checks -> "custom"
    for entry in host_config.custom_checks:
        services[('custom', entry['service_description'])] = (
            'custom',
            Service(
                check_plugin_name='custom',
                item=entry['service_description'],
                description=entry['service_description'],
                parameters=None,
            ),
        )

    # Similar for 'active_checks', but here we have parameters
    for plugin_name, entries in host_config.active_checks:
        for params in entries:
            descr = config.active_check_service_description(hostname, plugin_name, params)
            services[(plugin_name, descr)] = (
                'active',
                Service(
                    check_plugin_name=plugin_name,
                    item=descr,
                    description=descr,
                    parameters=params,
                ),
            )

    # Handle disabled services -> "ignored"
    for check_source, discovered_service in services.values():
        if check_source in ["legacy", "active", "custom"]:
            # These are ignored later in get_check_preview
            # TODO: This needs to be cleaned up. The problem here is that service_description() can not
            # calculate the description of active checks and the active checks need to be put into
            # "[source]_ignored" instead of ignored.
            continue

        # TODO(mo): centralize maincheckify: CMK-4295
        service_check_plugin_name = CheckPluginName(
            maincheckify(discovered_service.check_plugin_name))
        if config.service_ignored(hostname, service_check_plugin_name,
                                  discovered_service.description):
            services[(discovered_service.check_plugin_name, discovered_service.item)] = (
                "ignored",
                discovered_service,
            )

    return services


def _get_cluster_services(
    host_config: config.HostConfig,
    ipaddress: Optional[str],
    multi_host_sections: MultiHostSections,
    on_error: str,
) -> Tuple[ServicesTable, DiscoveredHostLabels]:
    cluster_items: ServicesTable = {}
    cluster_host_labels = DiscoveredHostLabels()
    if not host_config.nodes:
        return cluster_items, cluster_host_labels

    config_cache = config.get_config_cache()

    # Get services of the nodes. We are only interested in "old", "new" and "vanished"
    # From the states and parameters of these we construct the final state per service.
    for node in host_config.nodes:

        services, discovered_host_labels = _get_discovered_services(
            node,
            ip_lookup.lookup_ip_address(node),
            multi_host_sections,
            on_error,
        )
        cluster_host_labels.update(discovered_host_labels)
        for check_source, discovered_service in services.values():
            if host_config.hostname != config_cache.host_of_clustered_service(
                    node, discovered_service.description):
                continue  # not part of this host

            table_id = discovered_service.check_plugin_name, discovered_service.item
            if table_id not in cluster_items:
                cluster_items[table_id] = (check_source, discovered_service)
                continue

            first_check_source, first_discovered_service = cluster_items[table_id]
            if first_check_source == "old":
                continue

            if check_source == "old":
                cluster_items[table_id] = (check_source, discovered_service)
                continue

            if first_check_source == "vanished" and check_source == "new":
                cluster_items[table_id] = ("old", first_discovered_service)
                continue

            if check_source == "vanished" and first_check_source == "new":
                cluster_items[table_id] = ("old", discovered_service)
                continue

            # In all other cases either both must be "new" or "vanished" -> let it be

    # Now add manual and active serivce and handle ignored services
    return _merge_manual_services(host_config, cluster_items, on_error), cluster_host_labels


def get_check_preview(host_name: HostName, use_caches: bool, do_snmp_scan: bool,
                      on_error: str) -> Tuple[CheckPreviewTable, DiscoveredHostLabels]:
    """Get the list of service of a host or cluster and guess the current state of
    all services if possible"""
    host_config = config.get_config_cache().get_host_config(host_name)

    ip_address = None if host_config.is_cluster else ip_lookup.lookup_ip_address(host_name)

    multi_host_sections = data_sources.make_host_sections(
        host_config,
        ip_address,
        _get_sources_for_discovery(
            host_config,
            ip_address,
            do_snmp_scan=do_snmp_scan,
            on_error=on_error,
        ),
        max_cachefile_age=config.discovery_max_cachefile_age(use_caches),
    )

    services, discovered_host_labels = _get_host_services(
        host_config,
        ip_address,
        multi_host_sections,
        on_error,
    )

    table: CheckPreviewTable = []
    for check_source, service in services.values():
        # TODO (mo): centralize maincheckify: CMK-4295
        plugin_name = CheckPluginName(maincheckify(service.check_plugin_name))
        plugin = config.get_registered_check_plugin(plugin_name)
        params = _preview_params(host_name, service, plugin, check_source)

        if check_source in ['legacy', 'active', 'custom']:
            exitcode = None
            output = u"WAITING - %s check, cannot be done offline" % check_source.title()
            perfdata: List[Metric] = []
            ruleset_name: Optional[RulesetName] = None
        else:
            if plugin is None:
                continue  # Skip not existing check silently

            ruleset_name = str(plugin.check_ruleset_name) if plugin.check_ruleset_name else None
            wrapped_params = checking_types.Parameters(wrap_parameters(params))

            _submit, _data_rx, (exitcode, output, perfdata) = checking.get_aggregated_result(
                multi_host_sections,
                host_config,
                ip_address,
                service,
                plugin,
                lambda p=wrapped_params: p,  # type: ignore[misc]  # can't infer "type of lambda"
            )

        table.append((
            _preview_check_source(host_name, service, check_source),
            service.check_plugin_name,
            ruleset_name,
            service.item,
            # this `repr` is a result of various refactorings, I'm not sure it is needed.
            repr(service.parameters),
            params,
            service.description,
            exitcode,
            output,
            perfdata,
            service.service_labels.to_dict(),
        ))

    return table, discovered_host_labels


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
    plugin: Optional[checking_types.CheckPlugin],
    check_source: str,
) -> Optional[LegacyCheckParameters]:
    params: Optional[LegacyCheckParameters] = None

    if check_source not in ['legacy', 'active', 'custom']:
        if plugin is None:
            return params
        params = service.parameters
        if check_source != 'manual':
            params = check_table.get_precompiled_check_parameters(
                host_name,
                service.item,
                config.compute_check_parameters(
                    host_name,
                    service.check_plugin_name,
                    service.item,
                    params,
                ),
                service.check_plugin_name,
            )
        else:
            params = check_table.get_precompiled_check_parameters(
                host_name,
                service.item,
                params,
                service.check_plugin_name,
            )

    if check_source == "active":
        params = service.parameters

    if isinstance(params, config.TimespecificParamList):
        params = {
            "tp_computed_params": {
                "params": checking.legacy_determine_check_params(params),
                "computed_at": time.time(),
            }
        }

    return params
