#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
import os
import socket
import time
from typing import (
    Callable,
    Container,
    Counter,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
)

from six import ensure_binary

import livestatus

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.caching import config_cache as _config_cache
from cmk.utils.check_utils import worst_service_state, wrap_parameters
from cmk.utils.exceptions import MKGeneralException, MKTimeout
from cmk.utils.log import console
from cmk.utils.object_diff import make_object_diff
from cmk.utils.type_defs import (
    CheckPluginName,
    CheckPluginNameStr,
    DiscoveryResult,
    EVERYTHING,
    HostAddress,
    HostName,
    HostState,
    Item,
    MetricTuple,
    result as result_type,
    RulesetName,
    state_markers,
)

import cmk.core_helpers.cache
from cmk.core_helpers.host_sections import HostSections
from cmk.core_helpers.protocol import FetcherMessage
from cmk.core_helpers.type_defs import Mode, NO_SELECTION, SectionNameCollection

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.agent_based.decorator as decorator
import cmk.base.autochecks as autochecks
import cmk.base.check_table as check_table
import cmk.base.check_utils
import cmk.base.sources as sources
import cmk.base.agent_based.checking as checking
import cmk.base.config as config
import cmk.base.core
import cmk.base.crash_reporting
import cmk.base.section as section
from cmk.base.agent_based.data_provider import make_broker, ParsedSectionsBroker
from cmk.base.api.agent_based import checking_classes
from cmk.base.api.agent_based.type_defs import Parameters
from cmk.base.check_utils import LegacyCheckParameters, Service, ServiceID
from cmk.base.core_config import MonitoringCore
from cmk.base.discovered_labels import HostLabel

from ._discovered_services import analyse_discovered_services
from ._filters import ServiceFilters as _ServiceFilters
from ._host_labels import analyse_cluster_host_labels, analyse_host_labels
from .type_defs import DiscoveryParameters
from .utils import DiscoveryMode, TimeLimitFilter, QualifiedDiscovery

ServicesTable = Dict[ServiceID, Tuple[str, Service, List[HostName]]]
ServicesByTransition = Dict[str, List[autochecks.ServiceWithNodes]]

CheckPreviewEntry = Tuple[str, CheckPluginNameStr, Optional[RulesetName], Item,
                          LegacyCheckParameters, LegacyCheckParameters, str, Optional[int], str,
                          List[MetricTuple], Dict[str, str], List[HostName]]
CheckPreviewTable = List[CheckPreviewEntry]

_DiscoverySubresult = Tuple[int, List[str], List[str], List[Tuple], bool]

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


def _get_rediscovery_parameters(params: Dict) -> Dict:
    return params.get("inventory_rediscovery", {})


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
    run_plugin_names: Container[CheckPluginName],
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
            ipaddress = config.lookup_ip_address(host_config)
            parsed_sections_broker, _results = make_broker(
                config_cache=config_cache,
                host_config=host_config,
                ip_address=ipaddress,
                mode=mode,
                selected_sections=selected_sections,
                file_cache_max_age=config.discovery_max_cachefile_age() if use_caches else 0,
                fetcher_messages=(),
                force_snmp_cache_refresh=False,
                on_scan_error=on_error,
            )
            _do_discovery_for(
                host_name,
                ipaddress,
                parsed_sections_broker,
                run_plugin_names,
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
    run_plugin_names: Container[CheckPluginName],
    only_new: bool,
    discovery_parameters: DiscoveryParameters,
) -> None:

    host_labels = analyse_host_labels(
        host_name=host_name,
        ipaddress=ipaddress,
        parsed_sections_broker=parsed_sections_broker,
        discovery_parameters=discovery_parameters,
    )

    service_result = analyse_discovered_services(
        host_name=host_name,
        ipaddress=ipaddress,
        parsed_sections_broker=parsed_sections_broker,
        discovery_parameters=discovery_parameters,
        run_plugin_names=run_plugin_names,
        only_new=only_new,
    )

    # TODO (mo): for the labels the corresponding code is in _host_labels.
    # We should put the persisting and logging in one place.
    autochecks.save_autochecks_file(host_name, service_result.present)

    new_per_plugin = Counter(s.check_plugin_name for s in service_result.new)
    for name, count in sorted(new_per_plugin.items()):
        console.verbose("%s%3d%s %s\n" % (tty.green + tty.bold, count, tty.normal, name))

    section.section_success("%s, %s" % (
        f"Found {len(service_result.new)} services"
        if service_result.new else "Found no%s services" % (" new" if only_new else ""),
        f"{len(host_labels.new)} host labels" if host_labels.new else "no%s host labels" %
        (" new" if only_new else ""),
    ))


# determine changed services on host.
# param mode: can be one of "new", "remove", "fixall", "refresh", "only-host-labels"
# param servic_filter: if a filter is set, it controls whether items are touched by the discovery.
#                       if it returns False for a new item it will not be added, if it returns
#                       False for a vanished item, that item is kept
def discover_on_host(
    *,
    config_cache: config.ConfigCache,
    host_config: config.HostConfig,
    mode: DiscoveryMode,
    service_filters: Optional[_ServiceFilters],
    on_error: str,
    use_cached_snmp_data: bool,
    max_cachefile_age: int,
) -> DiscoveryResult:

    console.verbose("  Doing discovery with mode '%s'...\n" % mode)

    host_name = host_config.hostname
    result = DiscoveryResult()
    discovery_parameters = DiscoveryParameters(
        on_error=on_error,
        load_labels=(mode is not DiscoveryMode.REMOVE),
        save_labels=(mode is not DiscoveryMode.REMOVE),
        only_host_labels=(mode is DiscoveryMode.ONLY_HOST_LABELS),
    )

    if host_name not in config_cache.all_active_hosts():
        result.error_text = ""
        return result

    _set_cache_opts_of_checkers(use_cached_snmp_data=use_cached_snmp_data)

    try:
        # in "refresh" mode we first need to remove all previously discovered
        # checks of the host, so that _get_host_services() does show us the
        # new discovered check parameters.
        if mode is DiscoveryMode.REFRESH:
            result.self_removed += host_config.remove_autochecks()  # this is cluster-aware!

        if host_config.is_cluster:
            ipaddress = None
        else:
            ipaddress = config.lookup_ip_address(host_config)

        parsed_sections_broker, _source_results = make_broker(
            config_cache=config_cache,
            host_config=host_config,
            ip_address=ipaddress,
            mode=Mode.DISCOVERY,
            selected_sections=NO_SELECTION,
            file_cache_max_age=max_cachefile_age,
            fetcher_messages=(),
            force_snmp_cache_refresh=not use_cached_snmp_data,
            on_scan_error=on_error,
        )

        # Compute current state of new and existing checks
        services, host_labels = _get_host_services(
            host_config,
            ipaddress,
            parsed_sections_broker,
            discovery_parameters,
        )

        old_services = services.get("old", [])

        # Create new list of checks
        new_services = _get_post_discovery_services(host_name, services, service_filters or
                                                    _ServiceFilters.accept_all(), result, mode)
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

    else:
        if mode is not DiscoveryMode.REMOVE:
            result.self_new_host_labels = len(host_labels.new)
            result.self_total_host_labels = len(host_labels.present)

    result.self_total = result.self_new + result.self_kept
    return result


def _set_cache_opts_of_checkers(*, use_cached_snmp_data: bool) -> None:
    """Set caching options appropriate for discovery"""
    # TCP data sources should use the cache: Fetching live data may steal log
    # messages and the like from the checks.
    # However: Discovering new hosts might have no cache, so don't enforce it.
    cmk.core_helpers.cache.FileCacheFactory.use_outdated = True
    # As this is a change quite close to a release, I am leaving the following
    # line in. As far as I can tell, this property is never being read after the
    # callsites of this function.
    cmk.core_helpers.cache.FileCacheFactory.maybe = use_cached_snmp_data


def _make_services_audit_log_object(services: List[Service]) -> Set[str]:
    """The resulting object is used for building object diffs"""
    return {s.description for s in services}


def _get_post_discovery_services(
    host_name: HostName,
    services: ServicesByTransition,
    service_filters: _ServiceFilters,
    result: DiscoveryResult,
    mode: DiscoveryMode,
) -> List[autochecks.ServiceWithNodes]:
    """
    The output contains a selction of services in the states "new", "old", "ignored", "vanished"
    (depending on the value of `mode`) and "clusterd_".

    Service in with the state "custom", "legacy", "active" and "manual" are currently not checked.

    Note:

        Discovered checks that are shadowed by manual checks will vanish that way.

    """
    post_discovery_services: List[autochecks.ServiceWithNodes] = []
    for check_source, discovered_services_with_nodes in services.items():
        if check_source in ("custom", "legacy", "active", "manual"):
            # This is not an autocheck or ignored and currently not
            # checked. Note: Discovered checks that are shadowed by manual
            # checks will vanish that way.
            continue

        if check_source == "new":
            if mode in (DiscoveryMode.NEW, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH):
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
                if mode in (DiscoveryMode.FIXALL,
                            DiscoveryMode.REMOVE) and service_filters.vanished(
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


@decorator.handle_check_mk_check_result("discovery", "Check_MK Discovery")
def check_discovery(
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    *,
    # The next argument *must* remain optional for the DiscoCheckExecutor.
    #   See Also: `cmk.base.agent_based.checking.do_check()`.
    fetcher_messages: Sequence[FetcherMessage] = (),
) -> Tuple[int, List[str], List[str], List[Tuple]]:

    # Note: '--cache' is set in core_cmc, nagios template or even on CL and means:
    # 1. use caches as default:
    #    - Set FileCacheFactory.maybe = True (set max_cachefile_age, else 0)
    #    - Set FileCacheFactory.use_outdated = True
    # 2. Then these settings are used to read cache file or not

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

    discovery_mode = DiscoveryMode(_get_rediscovery_parameters(params).get("mode"))

    # In case of keepalive discovery we always have an ipaddress. When called as non keepalive
    # ipaddress is always None
    if ipaddress is None and not host_config.is_cluster:
        ipaddress = config.lookup_ip_address(host_config)

    parsed_sections_broker, source_results = make_broker(
        config_cache=config_cache,
        host_config=host_config,
        ip_address=ipaddress,
        mode=Mode.DISCOVERY,
        fetcher_messages=fetcher_messages,
        selected_sections=NO_SELECTION,
        file_cache_max_age=(config.discovery_max_cachefile_age()
                            if cmk.core_helpers.cache.FileCacheFactory.maybe else 0),
        force_snmp_cache_refresh=False,
        on_scan_error=discovery_parameters.on_error,
    )

    services, host_label_discovery_result = _get_host_services(
        host_config,
        ipaddress,
        parsed_sections_broker,
        discovery_parameters,
    )

    status, infotexts, long_infotexts, perfdata, need_rediscovery = _aggregate_subresults(
        _check_service_lists(host_name, services, params, discovery_mode),
        _check_host_labels(
            host_label_discovery_result,
            int(params.get("severity_new_host_label", 1)),
            discovery_mode,
        ),
        _check_data_sources(source_results),
    )

    if need_rediscovery:
        if host_config.is_cluster and host_config.nodes:
            for nodename in host_config.nodes:
                _set_rediscovery_flag(nodename)
        else:
            _set_rediscovery_flag(host_name)
        infotexts.append(u"rediscovery scheduled")

    return status, infotexts, long_infotexts, perfdata


def _aggregate_subresults(*subresults: _DiscoverySubresult) -> _DiscoverySubresult:
    stati, texts, long_texts, perfdata_list, need_rediscovery_flags = zip(*subresults)
    return (
        worst_service_state(*stati, default=0),
        sum(texts, []),
        sum(long_texts, []),
        sum(perfdata_list, []),
        any(need_rediscovery_flags),
    )


def _check_service_lists(
    host_name: HostName,
    services_by_transition: ServicesByTransition,
    params: config.DiscoveryCheckParameters,
    discovery_mode: DiscoveryMode,
) -> _DiscoverySubresult:

    status = 0
    infotexts = []
    long_infotexts = []
    perfdata: List[Tuple] = []
    need_rediscovery = False

    service_filters = _ServiceFilters.from_settings(_get_rediscovery_parameters(params))

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
            status = worst_service_state(status, st, default=0)
            infotexts.append(u"%d %s services (%s)%s" % (
                sum(affected_check_plugin_names.values()),
                title,
                info,
                state_markers[st],
            ))

            if (unfiltered and
                ((transition == "new" and discovery_mode in
                  (DiscoveryMode.NEW, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH)) or
                 (transition == "vanished" and discovery_mode in
                  (DiscoveryMode.REMOVE, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH)))):
                need_rediscovery = True
        else:
            infotexts.append(u"no %s services found" % title)

    for (discovered_service, _found_on_nodes) in services_by_transition.get("ignored", []):
        long_infotexts.append(
            u"ignored: %s: %s" %
            (discovered_service.check_plugin_name, discovered_service.description))

    return status, infotexts, long_infotexts, perfdata, need_rediscovery


def _check_host_labels(
    host_labels: QualifiedDiscovery[HostLabel],
    severity_new_host_label: int,
    discovery_mode: DiscoveryMode,
) -> _DiscoverySubresult:
    return (
        severity_new_host_label,
        [f"{len(host_labels.new)} new host labels"],
        [],
        [],
        discovery_mode in (DiscoveryMode.NEW, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH),
    ) if host_labels.new else (
        0,
        ["no new host labels"],
        [],
        [],
        False,
    )


def _check_data_sources(
    result: Sequence[Tuple[sources.Source, result_type.Result[HostSections, Exception]]],
) -> _DiscoverySubresult:
    summaries = [(source, source.summarize(host_sections)) for source, host_sections in result]
    return (
        worst_service_state(*(state for _s, (state, _t) in summaries), default=0),
        # Do not output informational (state = 0) things.  These information
        # are shown by the "Check_MK" service
        [f"[{src.id}] {text}" for src, (state, text) in summaries if state != 0],
        [],
        [],
        False,
    )


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

    oldest_queued = _queue_age()
    hosts = os.listdir(autodiscovery_dir)
    if not hosts:
        console.verbose("  Nothing to do. No hosts marked by discovery check.\n")

    # Fetch host state information from livestatus
    host_states = _fetch_host_states()
    activation_required = False
    rediscovery_reference_time = time.time()

    with TimeLimitFilter(limit=120, grace=10, label="hosts") as time_limited:
        for host_name in time_limited(hosts):
            host_config = config_cache.get_host_config(host_name)

            if not _discover_marked_host_exists(config_cache, host_name):
                continue

            # Only try to discover hosts with UP state
            if host_states and host_states.get(host_name) != 0:
                continue

            if _discover_marked_host(config_cache, host_config, rediscovery_reference_time,
                                     oldest_queued):
                activation_required = True

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

    reason = _may_rediscover(params, now_ts, oldest_queued)
    if not reason:
        result = discover_on_host(
            config_cache=config_cache,
            host_config=host_config,
            mode=DiscoveryMode(_get_rediscovery_parameters(params).get("mode")),
            service_filters=_ServiceFilters.from_settings(_get_rediscovery_parameters(params)),
            on_error="ignore",
            use_cached_snmp_data=True,
            # autodiscovery is run every 5 minutes (see
            # omd/packages/check_mk/skel/etc/cron.d/cmk_discovery)
            # make sure we may use the file the active discovery check left behind:
            max_cachefile_age=600,
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

    # we could check this earlier. No need to to it for every host.
    if now_ts - oldest_queued < rediscovery_parameters["group_time"]:
        return "last activation is too recent"

    return ""


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
) -> Tuple[ServicesByTransition, QualifiedDiscovery[HostLabel]]:

    host_labels = analyse_cluster_host_labels(
        host_config=host_config,
        ipaddress=ipaddress,
        parsed_sections_broker=parsed_sections_broker,
        discovery_parameters=discovery_parameters,
    ) if host_config.is_cluster else analyse_host_labels(
        host_name=host_config.hostname,
        ipaddress=ipaddress,
        parsed_sections_broker=parsed_sections_broker,
        discovery_parameters=discovery_parameters,
    )

    services = _get_cluster_services(
        host_config,
        ipaddress,
        parsed_sections_broker,
        discovery_parameters,
    ) if host_config.is_cluster else _get_node_services(
        host_config.hostname,
        ipaddress,
        parsed_sections_broker,
        discovery_parameters,
        config.get_config_cache().host_of_clustered_service,
    )

    # Now add manual and active service and handle ignored services
    return _merge_manual_services(host_config, services, discovery_parameters), host_labels


# Do the actual work for a non-cluster host or node
def _get_node_services(
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    parsed_sections_broker: ParsedSectionsBroker,
    discovery_parameters: DiscoveryParameters,
    host_of_clustered_service: Callable[[HostName, str], str],
) -> ServicesTable:

    service_result = analyse_discovered_services(
        host_name=host_name,
        ipaddress=ipaddress,
        parsed_sections_broker=parsed_sections_broker,
        discovery_parameters=discovery_parameters,
        run_plugin_names=EVERYTHING,
        only_new=False,
    )

    return {
        service.id(): (
            _node_service_source(
                check_source=check_source,
                host_name=host_name,
                cluster_name=host_of_clustered_service(host_name, service.description),
                service=service,
            ),
            service,
            [host_name],
        ) for check_source, service in itertools.chain(
            (("vanished", s) for s in service_result.vanished),
            (("old", s) for s in service_result.old),
            (("new", s) for s in service_result.new),
        )
    }


def _node_service_source(
    *,
    check_source: str,
    host_name: HostName,
    cluster_name: HostName,
    service: Service,
) -> str:
    if host_name == cluster_name:
        return check_source

    if config.service_ignored(cluster_name, service.check_plugin_name, service.description):
        return "ignored"

    return "clustered_" + check_source


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
        services_by_transition.setdefault(
            transition,
            [],
        ).append(autochecks.ServiceWithNodes(service, found_on_nodes))
    return services_by_transition


def _get_cluster_services(
    host_config: config.HostConfig,
    ipaddress: Optional[str],
    parsed_sections_broker: ParsedSectionsBroker,
    discovery_parameters: DiscoveryParameters,
) -> ServicesTable:

    if not host_config.nodes:
        return {}

    cluster_items: ServicesTable = {}
    config_cache = config.get_config_cache()

    # Get services of the nodes. We are only interested in "old", "new" and "vanished"
    # From the states and parameters of these we construct the final state per service.
    for node in host_config.nodes:
        node_config = config_cache.get_host_config(node)
        node_ipaddress = config.lookup_ip_address(node_config)

        services = analyse_discovered_services(
            host_name=node,
            ipaddress=node_ipaddress,
            parsed_sections_broker=parsed_sections_broker,
            discovery_parameters=discovery_parameters,
            run_plugin_names=EVERYTHING,
            only_new=True,
        )

        for check_source, service in itertools.chain(
            (("vanished", s) for s in services.vanished),
            (("old", s) for s in services.old),
            (("new", s) for s in services.new),
        ):
            cluster_items.update(
                _cluster_service_entry(
                    check_source=check_source,
                    host_name=host_config.hostname,
                    node_name=node,
                    services_cluster=config_cache.host_of_clustered_service(
                        node, service.description),
                    service=service,
                    existing_entry=cluster_items.get(service.id()),
                ))

    return cluster_items


def _cluster_service_entry(
    *,
    check_source: str,
    host_name: HostName,
    node_name: HostName,
    services_cluster: HostName,
    service: Service,
    existing_entry: Optional[Tuple[str, Service, List[HostName]]],
) -> Iterable[Tuple[ServiceID, Tuple[str, Service, List[HostName]]]]:
    if host_name != services_cluster:
        return  # not part of this host

    if existing_entry is None:
        yield service.id(), (check_source, service, [node_name])
        return

    first_check_source, existing_service, nodes_with_service = existing_entry
    if node_name not in nodes_with_service:
        nodes_with_service.append(node_name)

    if first_check_source == "old":
        return

    if check_source == "old":
        yield service.id(), (check_source, service, nodes_with_service)
        return

    if {first_check_source, check_source} == {"vanished", "new"}:
        yield existing_service.id(), ("old", existing_service, nodes_with_service)
        return

    # In all other cases either both must be "new" or "vanished" -> let it be


def get_check_preview(
    *,
    host_name: HostName,
    max_cachefile_age: int,
    use_cached_snmp_data: bool,
    on_error: str,
) -> Tuple[CheckPreviewTable, QualifiedDiscovery[HostLabel]]:
    """Get the list of service of a host or cluster and guess the current state of
    all services if possible"""
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(host_name)

    ip_address = None if host_config.is_cluster else config.lookup_ip_address(host_config)
    discovery_parameters = DiscoveryParameters(
        on_error=on_error,
        load_labels=True,
        save_labels=False,
        only_host_labels=False,
    )

    _set_cache_opts_of_checkers(use_cached_snmp_data=use_cached_snmp_data)

    parsed_sections_broker, _source_results = make_broker(
        config_cache=config_cache,
        host_config=host_config,
        ip_address=ip_address,
        mode=Mode.DISCOVERY,
        file_cache_max_age=max_cachefile_age,
        selected_sections=NO_SELECTION,
        fetcher_messages=(),
        force_snmp_cache_refresh=not use_cached_snmp_data,
        on_scan_error=on_error,
    )

    grouped_services, host_label_result = _get_host_services(
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

                ruleset_name = (str(plugin.check_ruleset_name)
                                if plugin and plugin.check_ruleset_name else None)
                wrapped_params = (Parameters(wrap_parameters(params)) if plugin and
                                  plugin.check_default_parameters is not None else None)

                exitcode, output, _perfdata = checking.get_aggregated_result(
                    parsed_sections_broker,
                    host_config,
                    ip_address,
                    service,
                    plugin,
                    lambda p=wrapped_params: p,  # type: ignore[misc]  # "type of lambda"
                ).result

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

    return table, host_label_result


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
