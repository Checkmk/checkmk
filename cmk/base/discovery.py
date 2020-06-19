#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import signal
import socket
import time
from types import FrameType
from typing import (
    Any,
    Callable,
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
)

from six import ensure_binary

import livestatus

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
    HostAddress,
    HostName,
    HostState,
    Item,
    Metric,
    PluginName,
    RulesetName,
    SourceType,
)
import cmk.utils.cleanup

import cmk.snmplib.snmp_scan as snmp_scan

from cmk.base.api.agent_based import checking_types
from cmk.base.api.agent_based.register.check_plugins import MANAGEMENT_NAME_PREFIX
from cmk.base.api.agent_based.register.check_plugins_legacy import (
    maincheckify,
    resolve_legacy_name,
    wrap_parameters,
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

from cmk.base.caching import config_cache as _config_cache
from cmk.base.check_utils import CheckParameters, DiscoveredService, FinalSectionContent
from cmk.base.core_config import MonitoringCore
from cmk.base.discovered_labels import DiscoveredHostLabels, HostLabel

# Run the discovery queued by check_discovery() - if any
_marked_host_discovery_timeout = 120

DiscoveredServicesTable = Dict[Tuple[check_table.CheckPluginName, check_table.Item],
                               Tuple[str, DiscoveredService]]
CheckPreviewEntry = Tuple[str, CheckPluginName, Optional[RulesetName], check_table.Item,
                          check_table.CheckParameters, check_table.CheckParameters, str,
                          Optional[int], str, List[Metric], Dict[str, str]]
CheckPreviewTable = List[CheckPreviewEntry]
DiscoveryEntry = Union[check_api_utils.Service, DiscoveredHostLabels, HostLabel,
                       Tuple[Item, CheckParameters]]
DiscoveryResult = List[DiscoveryEntry]
DiscoveryFunction = Callable[[FinalSectionContent], DiscoveryResult]

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
def do_discovery(arg_hostnames, arg_check_plugin_names, arg_only_new):
    # type: (Set[HostName], Optional[Set[CheckPluginName]], bool) -> None
    config_cache = config.get_config_cache()
    use_caches = not arg_hostnames or data_sources.abstract.DataSource.get_may_use_cache_file()
    on_error = "raise" if cmk.utils.debug.enabled() else "warn"

    host_names = _preprocess_hostnames(arg_hostnames, config_cache)
    check_plugin_names = {PluginName(maincheckify(n)) for n in arg_check_plugin_names
                         } if arg_check_plugin_names is not None else None

    # Now loop through all hosts
    for hostname in sorted(host_names):
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
                                     config.get_relevant_raw_sections(check_plugin_names))

            sources = _get_sources_for_discovery(
                hostname,
                ipaddress,
                do_snmp_scan,
                on_error,
                selected_raw_sections=selected_raw_sections,
            )

            multi_host_sections = _get_host_sections_for_discovery(sources, use_caches=use_caches)

            _do_discovery_for(hostname, ipaddress, multi_host_sections, check_plugin_names,
                              arg_only_new, on_error)

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            section.section_error("%s" % e)
        finally:
            cmk.utils.cleanup.cleanup_globals()


def _preprocess_hostnames(arg_host_names, config_cache):
    # type: (Set[HostName], config.ConfigCache) -> Set[HostName]
    """Default to all hosts and expand cluster names to their nodes"""
    if not arg_host_names:
        console.verbose("Discovering services on all hosts\n")
        arg_host_names = config_cache.all_active_realhosts()
    else:
        console.verbose("Discovering services on: %s\n" % ", ".join(sorted(arg_host_names)))

    host_names = set()  # type: Set[HostName]
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
        hostname,  # type: str
        ipaddress,  # type: Optional[str]
        multi_host_sections,  # type: data_sources.MultiHostSections
        check_plugin_names,  # type: Optional[Set[PluginName]]
        only_new,  # type: bool
        on_error,  # type: str
):
    # type: (...) -> None
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

    new_services = []  # type: List[DiscoveredService]

    if not check_plugin_names and not only_new:
        existing_services = []  # type: List[DiscoveredService]
    else:
        existing_services = autochecks.parse_autochecks_file(hostname, config.service_description)

    # Take over old items if -I is selected or if -II is selected with
    # --checks= and the check type is not one of the listed ones
    for existing_service in existing_services:
        service_plugin_name = PluginName(maincheckify(existing_service.check_plugin_name))
        if only_new or (check_plugin_names and service_plugin_name not in check_plugin_names):
            new_services.append(existing_service)

    services_per_plugin = {}  # type: Dict[check_table.CheckPluginName, int]
    for discovered_service in discovered_services:
        if discovered_service not in new_services:
            new_services.append(discovered_service)
            services_per_plugin.setdefault(discovered_service.check_plugin_name, 0)
            services_per_plugin[discovered_service.check_plugin_name] += 1

    autochecks.save_autochecks_file(hostname, new_services)

    section.section_step("Executing host label discovery")
    discovered_host_labels = _discover_host_labels(
        (hostname, ipaddress, SourceType.HOST),
        multi_host_sections,
        on_error=on_error,
    )
    discovered_host_labels += _discover_host_labels(
        (hostname, ipaddress, SourceType.MANAGEMENT),
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


def _perform_host_label_discovery(hostname, discovered_host_labels, only_new):
    # type: (str, DiscoveredHostLabels, bool) -> Tuple[DiscoveredHostLabels, Dict[check_table.CheckPluginName, int]]

    # Take over old items if -I is selected
    if only_new:
        return_host_labels = DiscoveredHostLabels.from_dict(
            DiscoveredHostLabelsStore(hostname).load())
    else:
        return_host_labels = DiscoveredHostLabels()

    new_host_labels_per_plugin = {}  # type: Dict[check_table.CheckPluginName, int]
    for discovered_label in discovered_host_labels.values():
        if discovered_label.name in return_host_labels:
            continue
        return_host_labels.add_label(discovered_label)
        new_host_labels_per_plugin.setdefault(discovered_label.plugin_name, 0)
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
        config_cache,  # type: config.ConfigCache
        host_config,  # type: config.HostConfig
        mode,  # type: str
        do_snmp_scan,  # type: bool
        use_caches,  # type: bool
        on_error="ignore",  # type: str
        service_filter=None,  # type: Callable
):
    # type: (...) -> Tuple[Dict[str, int], Optional[str]]
    hostname = host_config.hostname
    counts = {
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

    if hostname not in config_cache.all_active_hosts():
        return counts, ""

    if service_filter is None:
        service_filter = _accept_all_services

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

        sources = _get_sources_for_discovery(hostname,
                                             ipaddress,
                                             do_snmp_scan=do_snmp_scan,
                                             on_error=on_error,
                                             for_check_discovery=True)

        multi_host_sections = _get_host_sections_for_discovery(sources, use_caches=use_caches)

        # Compute current state of new and existing checks
        services, discovered_host_labels = _get_host_services(host_config,
                                                              ipaddress,
                                                              multi_host_sections,
                                                              on_error=on_error)

        # Create new list of checks
        new_items = []  # type: List[DiscoveredService]
        for check_source, discovered_service in services.values():
            if check_source in ("custom", "legacy", "active", "manual"):
                # This is not an autocheck or ignored and currently not
                # checked. Note: Discovered checks that are shadowed by manual
                # checks will vanish that way.
                continue

            if check_source == "new":
                if mode in ("new", "fixall", "refresh") and service_filter(
                        hostname, discovered_service.check_plugin_name, discovered_service.item):
                    counts["self_new"] += 1
                    new_items.append(discovered_service)

            elif check_source in ("old", "ignored"):
                # keep currently existing valid services in any case
                new_items.append(discovered_service)
                counts["self_kept"] += 1

            elif check_source == "vanished":
                # keep item, if we are currently only looking for new services
                # otherwise fix it: remove ignored and non-longer existing services
                if mode not in ("fixall", "remove") or not service_filter(
                        hostname, discovered_service.check_plugin_name, discovered_service.item):
                    new_items.append(discovered_service)
                    counts["self_kept"] += 1
                else:
                    counts["self_removed"] += 1

            elif check_source.startswith("clustered_"):
                # Silently keep clustered services
                counts[check_source] += 1
                new_items.append(discovered_service)

            else:
                raise MKGeneralException("Unknown check source '%s'" % check_source)
        host_config.set_autochecks(new_items)

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


def _accept_all_services(_hostname, _check_plugin_name, _item):
    return True


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
def check_discovery(hostname, ipaddress):
    # type: (str, Optional[str]) -> Tuple[int, List[str], List[str], List[Tuple]]
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    params = host_config.discovery_check_parameters
    if params is None:
        params = host_config.default_discovery_check_parameters()

    status = 0
    infotexts = []
    long_infotexts = []
    perfdata = []  # type: List[Tuple]

    # In case of keepalive discovery we always have an ipaddress. When called as non keepalive
    # ipaddress is always None
    if ipaddress is None and not host_config.is_cluster:
        ipaddress = ip_lookup.lookup_ip_address(hostname)

    sources = _get_sources_for_discovery(hostname,
                                         ipaddress,
                                         do_snmp_scan=params["inventory_check_do_scan"],
                                         on_error="raise")

    multi_host_sections = _get_host_sections_for_discovery(
        sources, use_caches=data_sources.abstract.DataSource.get_may_use_cache_file())

    services, discovered_host_labels = _get_host_services(host_config,
                                                          ipaddress,
                                                          multi_host_sections,
                                                          on_error="raise")

    need_rediscovery = False

    item_filters = _get_item_filter_func(params.get("inventory_rediscovery", {}))

    for check_state, title, params_key, default_state in [
        ("new", "unmonitored", "severity_unmonitored", config.inventory_check_severity),
        ("vanished", "vanished", "severity_vanished", 0),
    ]:

        affected_check_plugin_names = {}  # type: Dict[str, int]
        count = 0
        unfiltered = False

        for check_source, discovered_service in services.values():
            if check_source == check_state:
                count += 1
                affected_check_plugin_names.setdefault(discovered_service.check_plugin_name, 0)
                affected_check_plugin_names[discovered_service.check_plugin_name] += 1

                if not unfiltered and (item_filters is None or item_filters(
                        hostname, discovered_service.check_plugin_name, discovered_service.item)):
                    unfiltered = True

                long_infotexts.append(
                    u"%s: %s: %s" %
                    (title, discovered_service.check_plugin_name, discovered_service.description))

        if affected_check_plugin_names:
            info = ", ".join(["%s:%d" % e for e in affected_check_plugin_names.items()])
            st = params.get(params_key, default_state)
            status = cmk.base.utils.worst_service_state(status, st)
            infotexts.append(u"%d %s services (%s)%s" %
                             (count, title, info, check_api_utils.state_markers[st]))

            if params.get("inventory_rediscovery", False):
                mode = params["inventory_rediscovery"]["mode"]
                if (unfiltered and ((check_state == "new" and mode in (0, 2, 3)) or
                                    (check_state == "vanished" and mode in (1, 2, 3)))):
                    need_rediscovery = True
        else:
            infotexts.append(u"no %s services found" % title)

    for check_source, discovered_service in services.values():
        if check_source == "ignored":
            long_infotexts.append(
                u"ignored: %s: %s" %
                (discovered_service.check_plugin_name, discovered_service.description))

    _new_host_labels, host_labels_per_plugin = \
        _perform_host_label_discovery(hostname, discovered_host_labels, only_new=True)
    if host_labels_per_plugin:
        infotexts.append("%d new host labels" % sum(host_labels_per_plugin.values()))
        status = cmk.base.utils.worst_service_state(status,
                                                    params.get("severity_new_host_label", 1))

        if params.get("inventory_rediscovery", False):
            mode = params["inventory_rediscovery"]["mode"]
            if mode in (0, 2, 3):
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
    for source in sources.get_data_sources():
        source_state, source_output, _source_perfdata = source.get_summary_result_for_discovery()
        # Do not output informational (state = 0) things. These information are shown by the "Check_MK" service
        if source_state != 0:
            status = max(status, source_state)
            infotexts.append(u"[%s] %s" % (source.id(), source_output))

    return status, infotexts, long_infotexts, perfdata


def _set_rediscovery_flag(hostname):
    # type: (HostName) -> None
    def touch(filename):
        # type: (str) -> None
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


def _handle_discovery_timeout(signum, stack_frame):
    # type: (int, Optional[FrameType]) -> NoReturn
    raise DiscoveryTimeout()


def _set_discovery_timeout():
    # type: () -> None
    signal.signal(signal.SIGALRM, _handle_discovery_timeout)
    # Add an additional 10 seconds as grace period
    signal.alarm(_marked_host_discovery_timeout + 10)


def _clear_discovery_timeout():
    # type: () -> None
    signal.alarm(0)


def _get_autodiscovery_dir():
    # type: () -> str
    return cmk.utils.paths.var_dir + '/autodiscovery'


def discover_marked_hosts(core):
    # type: (MonitoringCore) -> None
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


def _fetch_host_states():
    # type: () -> Dict[HostName, HostState]
    try:
        query = "GET hosts\nColumns: name state"
        response = livestatus.LocalConnection().query(query)
        return {k: v for row in response for k, v in [_parse_row(row)]}
    except (livestatus.MKLivestatusNotFoundError, livestatus.MKLivestatusSocketError):
        pass
    return {}


def _parse_row(row):
    # type: (livestatus.LivestatusRow) -> Tuple[HostName, HostState]
    hostname, hoststate = row
    if isinstance(hostname, HostName) and isinstance(hoststate, HostState):
        return hostname, hoststate
    raise MKGeneralException("Invalid response from livestatus: %s" % row)


def _discover_marked_host_exists(config_cache, hostname):
    # type: (config.ConfigCache, HostName) -> bool
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


def _discover_marked_host(config_cache, host_config, now_ts, oldest_queued):
    # type: (config.ConfigCache, config.HostConfig, float, float) -> bool
    hostname = host_config.hostname
    something_changed = False

    mode_table = {0: "new", 1: "remove", 2: "fixall", 3: "refresh"}

    console.verbose("%s%s%s:\n" % (tty.bold, hostname, tty.normal))
    host_flag_path = os.path.join(_get_autodiscovery_dir(), hostname)

    params = host_config.discovery_check_parameters
    if params is None:
        console.verbose("  failed: discovery check disabled\n")
        return False

    item_filters = _get_item_filter_func(params.get("inventory_rediscovery", {}))

    why_not = _may_rediscover(params, now_ts, oldest_queued)
    if not why_not:
        redisc_params = params["inventory_rediscovery"]
        console.verbose("  Doing discovery with mode '%s'...\n" % mode_table[redisc_params["mode"]])
        result, error = discover_on_host(config_cache,
                                         host_config,
                                         mode_table[redisc_params["mode"]],
                                         do_snmp_scan=params["inventory_check_do_scan"],
                                         use_caches=True,
                                         service_filter=item_filters)
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
                if redisc_params["activation"]:
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


def _queue_age():
    # type: () -> float
    autodiscovery_dir = _get_autodiscovery_dir()
    oldest = time.time()
    for filename in os.listdir(autodiscovery_dir):
        oldest = min(oldest, os.path.getmtime(autodiscovery_dir + "/" + filename))
    return oldest


def _may_rediscover(params, now_ts, oldest_queued):
    # type: (config.DiscoveryCheckParameters, float, float) -> Optional[str]
    if "inventory_rediscovery" not in params:
        return "automatic discovery disabled for this host"

    now = time.gmtime(now_ts)
    for start_hours_mins, end_hours_mins in params["inventory_rediscovery"]["excluded_time"]:
        start_time = time.struct_time(
            (now.tm_year, now.tm_mon, now.tm_mday, start_hours_mins[0], start_hours_mins[1], 0,
             now.tm_wday, now.tm_yday, now.tm_isdst))

        end_time = time.struct_time((now.tm_year, now.tm_mon, now.tm_mday, end_hours_mins[0],
                                     end_hours_mins[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst))

        if start_time <= now <= end_time:
            return "we are currently in a disallowed time of day"

    if now_ts - oldest_queued < params["inventory_rediscovery"]["group_time"]:
        return "last activation is too recent"

    return None


def _get_item_filter_func(params_rediscovery):
    # type: (Dict[str, Any]) -> Optional[Callable[[HostName, CheckPluginName, Item], bool]]
    service_whitelist = params_rediscovery.get("service_whitelist")  # type: Optional[List[str]]
    service_blacklist = params_rediscovery.get("service_blacklist")  # type: Optional[List[str]]

    if not service_whitelist and not service_blacklist:
        return None

    if not service_whitelist:
        # whitelist. if none is specified, this matches everything
        service_whitelist = [".*"]

    if not service_blacklist:
        # blacklist. if none is specified, this matches nothing
        service_blacklist = ["(?!x)x"]

    whitelist = regex("|".join(["(%s)" % p for p in service_whitelist]))
    blacklist = regex("|".join(["(%s)" % p for p in service_blacklist]))

    return lambda hostname, check_plugin_name, item: _discovery_filter_by_lists(
        hostname, check_plugin_name, item, whitelist, blacklist)


def _discovery_filter_by_lists(hostname, check_plugin_name, item, whitelist, blacklist):
    # type: (HostName, CheckPluginName, Item, Pattern[str], Pattern[str]) -> bool
    description = config.service_description(hostname, check_plugin_name, item)
    return whitelist.match(description) is not None and blacklist.match(description) is None


#.
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
def schedule_discovery_check(hostname):
    # type: (HostName) -> None
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(cmk.utils.paths.livestatus_unix_socket)
        now = int(time.time())
        if 'cmk-inventory' in config.use_new_descriptions_for:
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
        host_key,  # type: data_sources.host_sections.HostKey
        multi_host_sections,  # type: data_sources.MultiHostSections
        on_error,  # type: str
):
    # type: (...) -> DiscoveredHostLabels
    discovered_host_labels = DiscoveredHostLabels()

    try:
        host_data = multi_host_sections.get_host_sections()[host_key]
    except KeyError:
        return discovered_host_labels

    try:
        raw_sections = [PluginName(n) for n in host_data.sections]
        # We do *not* process all available raw sections. Instead we see which *parsed*
        # sections would result from them, and then process those.
        section_plugins = (config.get_registered_section_plugin(rs) for rs in raw_sections)
        parsed_sections = {p.parsed_section_name for p in section_plugins if p is not None}

        console.vverbose("Trying host label discovery with: %s\n" %
                         ", ".join(str(p) for p in parsed_sections))
        for parsed_section_name in sorted(parsed_sections):
            try:
                plugin = config.get_parsed_section_creator(parsed_section_name, raw_sections)
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
        hostname,  # type: str
        ipaddress,  # type: Optional[str]
        multi_host_sections,  # type: data_sources.MultiHostSections
        on_error,  # type: str
        check_plugin_whitelist,  # type: Optional[Set[PluginName]]
):
    # type: (...) -> List[DiscoveredService]
    # Set host name for host_name()-function (part of the Check API)
    # (used e.g. by ps-discovery)
    check_api_utils.set_hostname(hostname)

    # find out which plugins we need to discover
    plugin_candidates = multi_host_sections.get_check_plugin_candidates()
    if check_plugin_whitelist is not None:
        plugin_candidates = plugin_candidates.intersection(check_plugin_whitelist)
    section.section_step("Executing discovery plugins (%d)" % len(plugin_candidates))
    console.vverbose("  Trying discovery with: %s\n" % ", ".join(str(n) for n in plugin_candidates))

    service_table = {}  # type: cmk.base.check_utils.DiscoveredCheckTable
    try:
        for check_plugin_name in sorted(plugin_candidates):
            try:
                for service in _execute_discovery(multi_host_sections, hostname, ipaddress,
                                                  check_plugin_name, on_error):
                    if not isinstance(service, DiscoveredService):
                        raise TypeError("unexpectedly discovered %r" % type(service))
                    service_table[(service.check_plugin_name, service.item)] = service
            except (KeyboardInterrupt, MKTimeout):
                raise
            except Exception as e:
                if on_error == "raise":
                    raise
                if on_error == "warn":
                    console.error("Discovery of '%s' failed: %s\n" % (check_plugin_name, e))

        check_table_formatted = check_table.remove_duplicate_checks(service_table)
        return list(check_table_formatted.values())

    except KeyboardInterrupt:
        raise MKGeneralException("Interrupted by Ctrl-C.")


def _get_sources_for_discovery(
        hostname,  # type: HostName
        ipaddress,  # type: Optional[HostAddress]
        do_snmp_scan,  # type: bool
        on_error,  # type: str
        for_check_discovery=False,  # type: bool
        *,
        selected_raw_sections=None,  # type: Optional[Dict[PluginName, config.SectionPlugin]]
):
    # type: (...) -> data_sources.DataSources
    sources = data_sources.DataSources(
        hostname,
        ipaddress,
        selected_raw_sections=selected_raw_sections,
    )

    for source in sources.get_data_sources():
        if isinstance(source, data_sources.SNMPDataSource):
            source.set_on_error(on_error)
            source.set_do_snmp_scan(do_snmp_scan)
            source.set_use_snmpwalk_cache(False)
            source.set_ignore_check_interval(True)

            # During discovery, the snmp datasource can never fully rely on the locally cached data,
            # since the available oid trees depend on the current running checks
            # We can not disable the data_source_cache per default when caching is set
            # since this would affect the WATO service discovery page.
            if for_check_discovery and source.get_may_use_cache_file():
                data_sources.SNMPDataSource.disable_data_source_cache()

            source.set_check_plugin_name_filter(snmp_scan.gather_available_raw_section_names,
                                                inventory=False)

    return sources


def _get_host_sections_for_discovery(sources, use_caches):
    # type: (data_sources.DataSources, bool) -> data_sources.MultiHostSections
    max_cachefile_age = config.inventory_max_cachefile_age if use_caches else 0
    return sources.get_host_sections(max_cachefile_age)


def _execute_discovery(
        multi_host_sections,  # type: data_sources.MultiHostSections
        hostname,  # type: str
        ipaddress,  # type: Optional[str]
        check_plugin_name,  # type: PluginName
        on_error,  # type: str
):
    # type: (...) -> Iterator[DiscoveredService]
    # Skip this check type if is ignored for that host
    if config.service_ignored(hostname, check_plugin_name, None):
        console.vverbose("  Skip ignored check plugin name '%s'\n" % check_plugin_name)
        return

    # TODO (mo): for now. the plan is to create management versions on the fly.
    source_type = (SourceType.MANAGEMENT if
                   str(check_plugin_name).startswith(MANAGEMENT_NAME_PREFIX) else SourceType.HOST)

    check_plugin = config.registered_check_plugins.get(check_plugin_name)
    if check_plugin is None:
        console.warning("  Missing check plugin: '%s'\n" % check_plugin_name)
        return

    try:
        kwargs = multi_host_sections.get_section_kwargs(
            (hostname, ipaddress, source_type),
            check_plugin.sections,
        )
    except Exception as exc:
        if cmk.utils.debug.enabled() or on_error == "raise":
            raise
        if on_error == "warn":
            console.warning("  Exception while parsing agent section: %s\n" % exc)
        return
    if not kwargs:
        return

    # TODO: add discovery parameters to kwargs CMK-4727

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
        hostname,  # type: HostName
        check_plugin_name,  # type: PluginName
        plugins_services,  # type: Iterable[checking_types.Service]
):
    # type: (...) -> Generator[DiscoveredService, None, None]
    for service in plugins_services:
        description = config.service_description(hostname, check_plugin_name, service.item)
        # make sanity check
        if len(description) == 0:
            console.error("%s: Check %s returned empty service description - ignoring it.\n" %
                          (hostname, check_plugin_name))
            continue

        yield DiscoveredService(
            check_plugin_name=resolve_legacy_name(check_plugin_name),
            item=service.item,
            description=description,
            parameters_unresolved=service.parameters,
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
def _get_host_services(host_config, ipaddress, multi_host_sections, on_error):
    # type: (config.HostConfig, Optional[str], data_sources.MultiHostSections, str) -> Tuple[DiscoveredServicesTable, DiscoveredHostLabels]
    if host_config.is_cluster:
        return _get_cluster_services(host_config, ipaddress, multi_host_sections, on_error)

    return _get_node_services(host_config, ipaddress, multi_host_sections, on_error)


# Do the actual work for a non-cluster host or node
def _get_node_services(
        host_config,  # type: config.HostConfig
        ipaddress,  # type: Optional[str]
        multi_host_sections,  # type: data_sources.MultiHostSections
        on_error,  # type: str
):
    # type: (...) -> Tuple[DiscoveredServicesTable, DiscoveredHostLabels]
    hostname = host_config.hostname
    services, discovered_host_labels = _get_discovered_services(hostname, ipaddress,
                                                                multi_host_sections, on_error)

    config_cache = config.get_config_cache()
    # Identify clustered services
    for check_source, discovered_service in services.values():
        clustername = config_cache.host_of_clustered_service(hostname,
                                                             discovered_service.description)
        if hostname != clustername:
            if config.service_ignored(clustername, discovered_service.check_plugin_name,
                                      discovered_service.description):
                check_source = "ignored"
            services[(discovered_service.check_plugin_name,
                      discovered_service.item)] = ("clustered_" + check_source, discovered_service)

    return _merge_manual_services(host_config, services, on_error), discovered_host_labels


# Part of _get_node_services that deals with discovered services
def _get_discovered_services(
        hostname,  # type: str
        ipaddress,  # type: Optional[str]
        multi_host_sections,  # type: data_sources.MultiHostSections
        on_error,  # type: str
):
    # type: (...) -> Tuple[DiscoveredServicesTable, DiscoveredHostLabels]
    # Create a dict from check_plugin_name/item to check_source/paramstring
    services = {}  # type: DiscoveredServicesTable

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
        (hostname, ipaddress, SourceType.HOST),
        multi_host_sections,
        on_error,
    )
    discovered_host_labels += _discover_host_labels(
        (hostname, ipaddress, SourceType.MANAGEMENT),
        multi_host_sections,
        on_error,
    )

    return services, discovered_host_labels


# TODO: Rename or extract disabled services handling
def _merge_manual_services(host_config, services, on_error):
    # type: (config.HostConfig, DiscoveredServicesTable, str) -> DiscoveredServicesTable
    """Add/replace manual and active checks and handle ignoration"""
    hostname = host_config.hostname

    # Find manual checks. These can override discovered checks -> "manual"
    manual_items = check_table.get_check_table(hostname, skip_autochecks=True)
    for service in manual_items.values():
        services[(service.check_plugin_name, service.item)] = (
            'manual',
            DiscoveredService(
                service.check_plugin_name,
                service.item,
                service.description,
                repr(service.parameters),
            ),
        )

    # Add custom checks -> "custom"
    for entry in host_config.custom_checks:
        services[('custom', entry['service_description'])] = (
            'custom',
            DiscoveredService(
                'custom',
                entry['service_description'],
                entry['service_description'],
                'None',
            ),
        )

    # Similar for 'active_checks', but here we have parameters
    for plugin_name, entries in host_config.active_checks:
        for params in entries:
            descr = config.active_check_service_description(hostname, plugin_name, params)
            services[(plugin_name, descr)] = (
                'active',
                DiscoveredService(
                    plugin_name,
                    descr,
                    descr,
                    repr(params),
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

        if config.service_ignored(hostname, discovered_service.check_plugin_name,
                                  discovered_service.description):
            services[(discovered_service.check_plugin_name, discovered_service.item)] = (
                "ignored",
                discovered_service,
            )

    return services


def _get_cluster_services(
        host_config,  # type: config.HostConfig
        ipaddress,  # type: Optional[str]
        multi_host_sections,  # type: data_sources.MultiHostSections
        on_error,  # type: str
):
    # type: (...) -> Tuple[DiscoveredServicesTable, DiscoveredHostLabels]
    cluster_items = {}  # type: DiscoveredServicesTable
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


def get_check_preview(host_name, use_caches, do_snmp_scan, on_error):
    # type: (HostName, bool, bool, str) -> Tuple[CheckPreviewTable, DiscoveredHostLabels]
    """Get the list of service of a host or cluster and guess the current state of
    all services if possible"""
    host_config = config.get_config_cache().get_host_config(host_name)

    ip_address = None if host_config.is_cluster else ip_lookup.lookup_ip_address(host_name)

    sources = _get_sources_for_discovery(
        host_name,
        ip_address,
        do_snmp_scan=do_snmp_scan,
        on_error=on_error,
    )

    multi_host_sections = _get_host_sections_for_discovery(sources, use_caches=use_caches)

    services, discovered_host_labels = _get_host_services(host_config, ip_address,
                                                          multi_host_sections, on_error)

    table = []  # type: CheckPreviewTable
    for check_source, discovered_service in services.values():
        # TODO (mo): centralize maincheckify: CMK-4295
        plugin_name = PluginName(maincheckify(discovered_service.check_plugin_name))
        plugin = config.get_registered_check_plugin(plugin_name)
        params = _preview_params(host_name, discovered_service, plugin, check_source)

        if check_source in ['legacy', 'active', 'custom']:
            exitcode = None
            output = u"WAITING - %s check, cannot be done offline" % check_source.title()
            perfdata = []  # type: List[Metric]
            ruleset_name = None  # type: Optional[RulesetName]
        else:
            if plugin is None:
                continue  # Skip not existing check silently

            ruleset_name = str(plugin.check_ruleset_name) if plugin.check_ruleset_name else None
            wrapped_params = checking_types.Parameters(wrap_parameters(params))

            _submit, _data_rx, (exitcode, output, perfdata) = checking.get_aggregated_result(
                multi_host_sections,
                host_config,
                ip_address,
                discovered_service,
                plugin,
                lambda p=wrapped_params: p,  # type: ignore[misc]  # can't infer "type of lambda"
            )

        table.append((
            _preview_check_source(host_name, discovered_service, check_source),
            discovered_service.check_plugin_name,
            ruleset_name,
            discovered_service.item,
            discovered_service.parameters_unresolved,
            params,
            discovered_service.description,
            exitcode,
            output,
            perfdata,
            discovered_service.service_labels.to_dict(),
        ))

    return table, discovered_host_labels


def _preview_check_source(
    host_name: HostName,
    discovered_service: DiscoveredService,
    check_source: str,
) -> str:
    if (check_source in ["legacy", "active", "custom"] and
            config.service_ignored(host_name, None, discovered_service.description)):
        return "%s_ignored" % check_source
    return check_source


def _preview_params(
    host_name: HostName,
    discovered_service: DiscoveredService,
    plugin: Optional[checking_types.CheckPlugin],
    check_source: str,
) -> Optional[CheckParameters]:
    params = None  # type: Optional[CheckParameters]

    if check_source not in ['legacy', 'active', 'custom']:
        if plugin is None:
            return params
        params = _get_check_parameters(discovered_service)
        if check_source != 'manual':
            params = check_table.get_precompiled_check_parameters(
                host_name,
                discovered_service.item,
                config.compute_check_parameters(
                    host_name,
                    discovered_service.check_plugin_name,
                    discovered_service.item,
                    params,
                ),
                discovered_service.check_plugin_name,
            )
        else:
            params = check_table.get_precompiled_check_parameters(
                host_name,
                discovered_service.item,
                params,
                discovered_service.check_plugin_name,
            )

    if check_source == "active":
        params = _get_check_parameters(discovered_service)

    if isinstance(params, config.TimespecificParamList):
        params = {
            "tp_computed_params": {
                "params": checking.legacy_determine_check_params(params),
                "computed_at": time.time(),
            }
        }

    return params


def _get_check_parameters(discovered_service):
    # type: (DiscoveredService) -> CheckParameters
    """Retrieves the check parameters (read from autochecks), possibly resolving a
    string to its actual value."""
    params = discovered_service.parameters_unresolved
    if not isinstance(params, str):
        return params
    try:
        check_context = config.get_check_context(discovered_service.check_plugin_name)
        # We can't simply access check_context[paramstring], because we may have
        # something like '{"foo": bar}'
        return eval(params, check_context, check_context)
    except Exception:
        raise MKGeneralException(
            "Invalid check parameter string '%s' found in discovered service %r" %
            (discovered_service.parameters_unresolved, discovered_service))
