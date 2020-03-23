#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import socket
import time
import signal
from types import FrameType  # pylint: disable=unused-import
from typing import (  # pylint: disable=unused-import
    Pattern, Union, Iterator, Callable, List, Text, Optional, Dict, Tuple, Set, NoReturn, Any,
)
import six

import livestatus

from cmk.utils.regex import regex
import cmk.utils.misc
import cmk.utils.tty as tty
import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.labels import DiscoveredHostLabelsStore
from cmk.utils.exceptions import MKGeneralException, MKTimeout
from cmk.utils.encoding import convert_to_unicode
from cmk.utils.exceptions import MKException

from cmk.base.caching import config_cache as _config_cache
import cmk.base.crash_reporting
import cmk.base.config as config
import cmk.base.console as console
import cmk.base.ip_lookup as ip_lookup
import cmk.base.check_api_utils as check_api_utils
import cmk.base.item_state as item_state
import cmk.base.checking as checking
import cmk.base.data_sources as data_sources
import cmk.base.check_table as check_table
import cmk.base.autochecks as autochecks
import cmk.base.core
import cmk.base.cleanup
import cmk.base.check_utils
import cmk.base.decorator
import cmk.base.snmp_scan as snmp_scan
from cmk.base.exceptions import MKParseFunctionError
import cmk.base.utils
from cmk.utils.type_defs import HostName, HostAddress  # pylint: disable=unused-import
from cmk.base.core_config import MonitoringCore  # pylint: disable=unused-import
from cmk.base.check_utils import (  # pylint: disable=unused-import
    CheckPluginName, CheckParameters, DiscoveredService, Item, ServiceState, Metric, RulesetName,
    HostState, FinalSectionContent,
)
from cmk.base.discovered_labels import (
    DiscoveredServiceLabels,
    DiscoveredHostLabels,
    HostLabel,
)

# Run the discovery queued by check_discovery() - if any
_marked_host_discovery_timeout = 120

DiscoveredServicesTable = Dict[Tuple[check_table.CheckPluginName, check_table.Item],
                               Tuple[str, DiscoveredService]]
CheckPreviewEntry = Tuple[str, CheckPluginName, Optional[RulesetName], check_table.Item,
                          check_table.CheckParameters, check_table.CheckParameters, Text,
                          Optional[int], Text, List[Metric], Dict[Text, Text]]
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
def do_discovery(hostnames, check_plugin_names, only_new):
    # type: (Set[HostName], Optional[Set[CheckPluginName]], bool) -> None
    config_cache = config.get_config_cache()
    use_caches = data_sources.abstract.DataSource.get_may_use_cache_file()
    if not hostnames:
        console.verbose("Discovering services on all hosts\n")
        hostnames = config_cache.all_active_realhosts()
        use_caches = True
    else:
        console.verbose("Discovering services on: %s\n" % ", ".join(sorted(hostnames)))

    # For clusters add their nodes to the list. Clusters itself
    # cannot be discovered but the user is allowed to specify
    # them and we do discovery on the nodes instead.
    cluster_hosts = []
    for h in hostnames:
        host_config = config_cache.get_host_config(h)
        if host_config.is_cluster:
            cluster_hosts.append(h)
            nodes = host_config.nodes
            if nodes is None:
                raise MKGeneralException("Invalid cluster configuration")
            hostnames.update(nodes)

    # Then remove clusters and make list unique
    sorted_hostnames = sorted(
        {h for h in hostnames if not config_cache.get_host_config(h).is_cluster})

    # Now loop through all hosts
    for hostname in sorted_hostnames:
        console.section_begin(hostname)

        try:
            if cmk.utils.debug.enabled():
                on_error = "raise"
            else:
                on_error = "warn"

            ipaddress = ip_lookup.lookup_ip_address(hostname)

            # Usually we disable SNMP scan if cmk -I is used without a list of
            # explicity hosts. But for host that have never been service-discovered
            # yet (do not have autochecks), we enable SNMP scan.
            do_snmp_scan = not use_caches or not autochecks.has_autochecks(hostname)

            sources = _get_sources_for_discovery(hostname, ipaddress, check_plugin_names,
                                                 do_snmp_scan, on_error)
            multi_host_sections = _get_host_sections_for_discovery(sources, use_caches=use_caches)

            _do_discovery_for(hostname, ipaddress, sources, multi_host_sections, check_plugin_names,
                              only_new, on_error)

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            console.section_error("%s" % e)
        finally:
            cmk.base.cleanup.cleanup_globals()

    # Check whether or not the cluster host autocheck files are still
    # existant. Remove them. The autochecks are only stored in the nodes
    # autochecks files these days.
    for hostname in cluster_hosts:
        autochecks.remove_autochecks_file(hostname)


def _do_discovery_for(hostname, ipaddress, sources, multi_host_sections, check_plugin_names,
                      only_new, on_error):
    # type: (str, Optional[str], data_sources.DataSources, data_sources.MultiHostSections, Optional[Set[CheckPluginName]], bool, str) -> None
    if not check_plugin_names:
        # In 'multi_host_sections = _get_host_sections_for_discovery(..)'
        # we've already discovered the right check plugin names.
        # _discover_services(..) would discover check plugin names again.
        # In order to avoid a second discovery (SNMP data source would do
        # another SNMP scan) we enforce this selection to be used.
        check_plugin_names = multi_host_sections.get_check_plugin_names()
        sources.enforce_check_plugin_names(check_plugin_names)

    console.step("Executing discovery plugins (%d)" % len(check_plugin_names))
    console.vverbose("  Trying discovery with: %s\n" % ", ".join(check_plugin_names))
    discovered_services, discovered_host_labels = _discover_services(hostname,
                                                                     ipaddress,
                                                                     sources,
                                                                     multi_host_sections,
                                                                     on_error=on_error)

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
        if only_new or (check_plugin_names and
                        existing_service.check_plugin_name not in check_plugin_names):
            new_services.append(existing_service)

    services_per_plugin = {}  # type: Dict[check_table.CheckPluginName, int]
    for discovered_service in discovered_services:
        if discovered_service not in new_services:
            new_services.append(discovered_service)
            services_per_plugin.setdefault(discovered_service.check_plugin_name, 0)
            services_per_plugin[discovered_service.check_plugin_name] += 1

    autochecks.save_autochecks_file(hostname, new_services)

    new_host_labels, host_labels_per_plugin = \
        _perform_host_label_discovery(hostname, discovered_host_labels, check_plugin_names, only_new)
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

    console.section_success(", ".join(messages))


def _perform_host_label_discovery(hostname, discovered_host_labels, check_plugin_names, only_new):
    # type: (str, DiscoveredHostLabels, Optional[Set[CheckPluginName]], bool) -> Tuple[DiscoveredHostLabels, Dict[check_table.CheckPluginName, int]]

    new_host_labels = DiscoveredHostLabels()

    if not check_plugin_names and not only_new:
        existing_host_labels = DiscoveredHostLabels()
    else:
        existing_host_labels = DiscoveredHostLabels.from_dict(
            DiscoveredHostLabelsStore(hostname).load())

    # Take over old items if -I is selected or if -II is selected with
    # --checks= and the check type is not one of the listed ones
    for existing_label in existing_host_labels.values():
        if only_new or (check_plugin_names and
                        existing_label.plugin_name not in check_plugin_names):
            new_host_labels.add_label(existing_label)

    host_labels_per_plugin = {}  # type: Dict[check_table.CheckPluginName, int]
    for discovered_label in discovered_host_labels.values():
        if discovered_label.name not in new_host_labels:
            new_host_labels.add_label(discovered_label)
            host_labels_per_plugin.setdefault(discovered_label.plugin_name, 0)
            host_labels_per_plugin[discovered_label.plugin_name] += 1

    return new_host_labels, host_labels_per_plugin


# determine changed services on host.
# param mode: can be one of "new", "remove", "fixall", "refresh"
# param do_snmp_scan: if True, a snmp host will be scanned, otherwise uses only the check types
#                     previously discovereda
# param servic_filter: if a filter is set, it controls whether items are touched by the discovery.
#                       if it returns False for a new item it will not be added, if it returns
#                       False for a vanished item, that item is kept
def discover_on_host(config_cache,
                     host_config,
                     mode,
                     do_snmp_scan,
                     use_caches,
                     on_error="ignore",
                     service_filter=None):
    # type: (config.ConfigCache, config.HostConfig, str, bool, bool, str, Callable) -> Tuple[Dict[str, int], Optional[str]]
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

    if hostname not in config_cache.all_active_realhosts():
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
                                             check_plugin_names=None,
                                             do_snmp_scan=do_snmp_scan,
                                             on_error=on_error)

        multi_host_sections = _get_host_sections_for_discovery(sources, use_caches=use_caches)

        # Compute current state of new and existing checks
        services, discovered_host_labels = _get_host_services(host_config,
                                                              ipaddress,
                                                              sources,
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
            _perform_host_label_discovery(hostname, discovered_host_labels, check_plugin_names=None, only_new=True)
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
    # type: (str, Optional[str]) -> Tuple[int, List[Text], List[Text], List[Tuple]]
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
                                         check_plugin_names=None,
                                         do_snmp_scan=params["inventory_check_do_scan"],
                                         on_error="raise")

    multi_host_sections = _get_host_sections_for_discovery(
        sources, use_caches=data_sources.abstract.DataSource.get_may_use_cache_file())

    services, discovered_host_labels = _get_host_services(host_config,
                                                          ipaddress,
                                                          sources,
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
        _perform_host_label_discovery(hostname, discovered_host_labels, check_plugin_names=None, only_new=True)
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

        s.send(six.ensure_binary("COMMAND [%d] %s\n" % (now, command)))
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
def _discover_services(hostname, ipaddress, sources, multi_host_sections, on_error):
    # type: (str, Optional[str], data_sources.DataSources, data_sources.MultiHostSections, str) -> Tuple[List[DiscoveredService], DiscoveredHostLabels]
    # Set host name for host_name()-function (part of the Check API)
    # (used e.g. by ps-discovery)
    check_api_utils.set_hostname(hostname)

    discovered_services = []  # type: List[DiscoveredService]
    discovered_host_labels = DiscoveredHostLabels()
    try:
        for check_plugin_name in sources.get_check_plugin_names():
            try:
                for entry in _execute_discovery(multi_host_sections, hostname, ipaddress,
                                                check_plugin_name, on_error):
                    if isinstance(entry, DiscoveredService):
                        discovered_services.append(entry)
                    elif isinstance(entry, HostLabel):
                        entry.plugin_name = check_plugin_name
                        discovered_host_labels.add_label(entry)
                    elif isinstance(entry, DiscoveredHostLabels):
                        for host_label in entry.values():
                            host_label.plugin_name = check_plugin_name
                            discovered_host_labels.add_label(host_label)
            except (KeyboardInterrupt, MKTimeout):
                raise
            except Exception as e:
                if on_error == "raise":
                    raise
                if on_error == "warn":
                    console.error("Discovery of '%s' failed: %s\n" % (check_plugin_name, e))

        check_table_formatted = {}  # type: check_table.CheckTable
        for discovered_service in discovered_services:
            check_table_formatted[(discovered_service.check_plugin_name,
                                   discovered_service.item)] = discovered_service

        check_table_formatted = check_table.remove_duplicate_checks(check_table_formatted)
        for discovered_service in discovered_services[:]:
            if (discovered_service.check_plugin_name,
                    discovered_service.item) not in check_table_formatted:
                discovered_services.remove(discovered_service)

        return discovered_services, discovered_host_labels

    except KeyboardInterrupt:
        raise MKGeneralException("Interrupted by Ctrl-C.")


def _get_sources_for_discovery(hostname, ipaddress, check_plugin_names, do_snmp_scan, on_error):
    # type: (HostName, Optional[HostAddress], Optional[Set[CheckPluginName]], bool, str) -> data_sources.DataSources
    sources = data_sources.DataSources(hostname, ipaddress)

    for source in sources.get_data_sources():
        if isinstance(source, data_sources.SNMPDataSource):
            source.set_on_error(on_error)
            source.set_do_snmp_scan(do_snmp_scan)
            source.set_use_snmpwalk_cache(False)
            source.set_ignore_check_interval(True)
            source.set_check_plugin_name_filter(snmp_scan.gather_snmp_check_plugin_names)

    # When check types are specified via command line, enforce them and disable auto detection
    if check_plugin_names:
        sources.enforce_check_plugin_names(check_plugin_names)

    return sources


def _get_host_sections_for_discovery(sources, use_caches):
    # type: (data_sources.DataSources, bool) -> data_sources.MultiHostSections
    max_cachefile_age = config.inventory_max_cachefile_age if use_caches else 0
    return sources.get_host_sections(max_cachefile_age)


def _execute_discovery(multi_host_sections, hostname, ipaddress, check_plugin_name, on_error):
    # type: (data_sources.MultiHostSections, str, Optional[str], str, str) -> Iterator[Union[DiscoveredService, DiscoveredHostLabels, HostLabel]]
    # Skip this check type if is ignored for that host
    if config.service_ignored(hostname, check_plugin_name, None):
        console.vverbose("  Skip ignored check plugin name '%s'\n" % check_plugin_name)
        return

    try:
        # TODO: There is duplicate code with checking.execute_check(). Find a common place!
        try:
            section_content = multi_host_sections.get_section_content(hostname,
                                                                      ipaddress,
                                                                      check_plugin_name,
                                                                      for_discovery=True)
        except MKParseFunctionError as e:
            if cmk.utils.debug.enabled() or on_error == "raise":
                x = e.exc_info()
                if x[0] == item_state.MKCounterWrapped:
                    return
                # re-raise the original exception to not destory the trace. This may raise a MKCounterWrapped
                # exception which need to lead to a skipped check instead of a crash
                # TODO CMK-3729, PEP-3109
                new_exception = x[0](x[1])
                new_exception.__traceback__ = x[2]  # type: ignore[attr-defined]
                raise new_exception

            if on_error == "warn":
                section_name = cmk.base.check_utils.section_name_of(check_plugin_name)
                console.warning("Exception while parsing agent section '%s': %s\n" %
                                (section_name, e))

            return

        if section_content is None:  # No data for this check type
            return

        # In case of SNMP checks but missing agent response, skip this check.
        # TODO: This feature predates the 'parse_function', and is not needed anymore.
        # # Special checks which still need to be called even with empty data
        # # may declare this.
        if not section_content and cmk.base.check_utils.is_snmp_check(check_plugin_name) \
           and not config.check_info[check_plugin_name]["handle_empty_info"]:
            return

        # Now do the actual discovery
        discovery_function = _get_discovery_function_of(check_plugin_name)
        discovered_items = _execute_discovery_function(discovery_function, section_content)
        for entry in _validate_discovered_items(hostname, check_plugin_name, discovered_items):
            yield entry
    except Exception as e:
        if on_error == "warn":
            console.warning("  Exception in discovery function of check type '%s': %s" %
                            (check_plugin_name, e))
        elif on_error == "raise":
            raise


def _get_discovery_function_of(check_plugin_name):
    # type: (CheckPluginName) -> DiscoveryFunction
    try:
        discovery_function = config.check_info[check_plugin_name]["inventory_function"]
    except KeyError:
        raise MKGeneralException("No such check type '%s'" % check_plugin_name)

    if discovery_function is None:
        return lambda _info: _no_discovery_possible(check_plugin_name)

    discovery_function_args = cmk.utils.misc.getfuncargs(discovery_function)
    if len(discovery_function_args) != 1:
        raise MKGeneralException(
            "The discovery function \"%s\" of the check \"%s\" is expected to take a "
            "single argument (info or parsed), but it's taking the following arguments: %r. "
            "You will have to change the arguments of the discovery function to make it "
            "compatible with this Checkmk version." %
            (discovery_function.__name__, check_plugin_name, discovery_function_args))

    return discovery_function


def _no_discovery_possible(check_plugin_name):
    # type: (CheckPluginName) -> List
    console.verbose("%s does not support discovery. Skipping it.\n", check_plugin_name)
    return []


# FIXME: The whole typing here is fundamentally broken and actually a lie: We
# don't have any static guarantees about the discovery function, so the type
# below is just wishful thinking. We only know something *after* validation,
# but that is a dynamic thing...
def _execute_discovery_function(discovery_function, section_content):
    # type: (DiscoveryFunction, FinalSectionContent) -> DiscoveryResult
    discovered_items = discovery_function(section_content)

    # tolerate function not explicitely returning []
    if discovered_items is None:
        discovered_items = []

    # New yield based api style
    elif not isinstance(discovered_items, list):
        discovered_items = list(discovered_items)

    return discovered_items


# FIXME: Broken typing, see comment for _execute_discovery_function.
def _validate_discovered_items(hostname, check_plugin_name, discovered_items):
    # type: (str, CheckPluginName, DiscoveryResult) -> Iterator[Union[DiscoveredService, DiscoveredHostLabels, HostLabel]]
    for entry in discovered_items:
        if isinstance(entry, check_api_utils.Service):
            item = entry.item
            parameters_unresolved = entry.parameters
            service_labels = entry.service_labels
            yield entry.host_labels

        elif isinstance(entry, (DiscoveredHostLabels, HostLabel)):
            yield entry
            continue

        elif isinstance(entry, tuple):
            service_labels = DiscoveredServiceLabels()
            if len(entry) == 2:  # comment is now obsolete
                item, parameters_unresolved = entry
            elif len(entry) == 3:  # allow old school
                # FIXME: Broken typing, see comment for _execute_discovery_function.
                item, __, parameters_unresolved = entry  # type: ignore[misc]
            else:
                # we really don't want longer tuples (or 1-tuples).
                console.error(
                    "%s: Check %s returned invalid discovery data (not 2 or 3 elements): %r\n" %
                    (hostname, check_plugin_name, repr(entry)))
                continue
        else:
            console.error("%s: Check %s returned invalid discovery data (entry not a tuple): %r\n" %
                          (hostname, check_plugin_name, repr(entry)))
            continue

        # Check_MK 1.2.7i3 defines items to be unicode strings. Convert non unicode
        # strings here seamless. TODO remove this conversion one day and replace it
        # with a validation that item needs to be of type unicode
        if isinstance(item, str):
            item = convert_to_unicode(item)

        description = config.service_description(hostname, check_plugin_name, item)
        # make sanity check
        if len(description) == 0:
            console.error("%s: Check %s returned empty service description - ignoring it.\n" %
                          (hostname, check_plugin_name))
            continue

        yield DiscoveredService(
            check_plugin_name=check_plugin_name,
            item=item,
            description=description,
            parameters_unresolved=parameters_unresolved,
            service_labels=service_labels,
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
def _get_host_services(host_config, ipaddress, sources, multi_host_sections, on_error):
    # type: (config.HostConfig, Optional[str], data_sources.DataSources, data_sources.MultiHostSections, str) -> Tuple[DiscoveredServicesTable, DiscoveredHostLabels]
    if host_config.is_cluster:
        return _get_cluster_services(host_config, ipaddress, sources, multi_host_sections, on_error)

    return _get_node_services(host_config, ipaddress, sources, multi_host_sections, on_error)


# Do the actual work for a non-cluster host or node
def _get_node_services(host_config, ipaddress, sources, multi_host_sections, on_error):
    # type: (config.HostConfig, Optional[str], data_sources.DataSources, data_sources.MultiHostSections, str) -> Tuple[DiscoveredServicesTable, DiscoveredHostLabels]
    hostname = host_config.hostname
    services, discovered_host_labels = _get_discovered_services(hostname, ipaddress, sources,
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
def _get_discovered_services(hostname, ipaddress, sources, multi_host_sections, on_error):
    # type: (str, Optional[str], data_sources.DataSources, data_sources.MultiHostSections, str) -> Tuple[DiscoveredServicesTable, DiscoveredHostLabels]
    # Create a dict from check_plugin_name/item to check_source/paramstring
    services = {}  # type: DiscoveredServicesTable

    # In 'multi_host_sections = _get_host_sections_for_discovery(..)'
    # we've already discovered the right check plugin names.
    # _discover_services(..) would discover check plugin names again.
    # In order to avoid a second discovery (SNMP data source would do
    # another SNMP scan) we enforce this selection to be used.
    check_plugin_names = multi_host_sections.get_check_plugin_names()
    sources.enforce_check_plugin_names(check_plugin_names)

    # Handle discovered services -> "new"
    discovered_services, discovered_host_labels = _discover_services(hostname, ipaddress, sources,
                                                                     multi_host_sections, on_error)
    for discovered_service in discovered_services:
        services.setdefault((discovered_service.check_plugin_name, discovered_service.item),
                            ("new", discovered_service))

    # Match with existing items -> "old" and "vanished"
    for existing_service in autochecks.parse_autochecks_file(hostname, config.service_description):
        table_id = existing_service.check_plugin_name, existing_service.item
        check_source = "vanished" if table_id not in services else "old"
        services[table_id] = check_source, existing_service

    return services, discovered_host_labels


# TODO: Rename or extract disabled services handling
def _merge_manual_services(host_config, services, on_error):
    # type: (config.HostConfig, DiscoveredServicesTable, str) -> DiscoveredServicesTable
    """Add/replace manual and active checks and handle ignoration"""
    hostname = host_config.hostname

    # Find manual checks. These can override discovered checks -> "manual"
    manual_items = check_table.get_check_table(hostname, skip_autochecks=True)
    for service in manual_items.values():
        services[(service.check_plugin_name,
                  service.item)] = ('manual',
                                    DiscoveredService(service.check_plugin_name,
                                                      service.item, service.description,
                                                      repr(service.parameters)))

    # Add custom checks -> "custom"
    for entry in host_config.custom_checks:
        services[('custom',
                  entry['service_description'])] = ('custom',
                                                    DiscoveredService('custom',
                                                                      entry['service_description'],
                                                                      entry['service_description'],
                                                                      'None'))

    # Similar for 'active_checks', but here we have parameters
    for plugin_name, entries in host_config.active_checks:
        for params in entries:
            descr = config.active_check_service_description(hostname, plugin_name, params)
            services[(plugin_name, descr)] = ('active',
                                              DiscoveredService(plugin_name, descr, descr,
                                                                repr(params)))

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
            services[(discovered_service.check_plugin_name,
                      discovered_service.item)] = ("ignored", discovered_service)

    return services


def _get_cluster_services(host_config, ipaddress, sources, multi_host_sections, on_error):
    # type: (config.HostConfig, Optional[str], data_sources.DataSources, data_sources.MultiHostSections, str) -> Tuple[DiscoveredServicesTable, DiscoveredHostLabels]
    config_cache = config.get_config_cache()

    # Get setting from cluster SNMP data source
    do_snmp_scan = False
    for source in sources.get_data_sources():
        if isinstance(source, data_sources.SNMPDataSource):
            do_snmp_scan = source.get_do_snmp_scan()

    cluster_items = {}  # type: DiscoveredServicesTable
    cluster_host_labels = DiscoveredHostLabels()
    if not host_config.nodes:
        return cluster_items, cluster_host_labels

    # Get services of the nodes. We are only interested in "old", "new" and "vanished"
    # From the states and parameters of these we construct the final state per service.
    for node in host_config.nodes:
        node_ipaddress = ip_lookup.lookup_ip_address(node)
        node_sources = _get_sources_for_discovery(
            node,
            node_ipaddress,
            check_plugin_names=sources.get_enforced_check_plugin_names(),
            do_snmp_scan=do_snmp_scan,
            on_error=on_error,
        )

        services, discovered_host_labels = _get_discovered_services(node, node_ipaddress,
                                                                    node_sources,
                                                                    multi_host_sections, on_error)
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


# TODO: Can't we reduce the duplicate code here? Check out the "checking" code
def get_check_preview(hostname, use_caches, do_snmp_scan, on_error):
    # type: (HostName, bool, bool, str) -> Tuple[CheckPreviewTable, DiscoveredHostLabels]
    """Get the list of service of a host or cluster and guess the current state of
    all services if possible"""
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    if host_config.is_cluster:
        ipaddress = None
    else:
        ipaddress = ip_lookup.lookup_ip_address(hostname)

    sources = _get_sources_for_discovery(hostname,
                                         ipaddress,
                                         check_plugin_names=None,
                                         do_snmp_scan=do_snmp_scan,
                                         on_error=on_error)

    multi_host_sections = _get_host_sections_for_discovery(sources, use_caches=use_caches)

    services, discovered_host_labels = _get_host_services(host_config, ipaddress, sources,
                                                          multi_host_sections, on_error)

    table = []  # type: CheckPreviewTable
    for check_source, discovered_service in services.values():
        params = None  # type: Optional[CheckParameters]
        exitcode = None  # type: Optional[ServiceState]
        perfdata = []  # type: List[Metric]
        if check_source not in ['legacy', 'active', 'custom']:
            if discovered_service.check_plugin_name not in config.check_info:
                continue  # Skip not existing check silently

            # apply check_parameters
            try:
                params = _get_check_parameters(discovered_service)
            except Exception:
                raise MKGeneralException(
                    "Invalid check parameter string '%s' found in discovered service %r" %
                    (discovered_service.parameters_unresolved, discovered_service))

            check_api_utils.set_service(discovered_service.check_plugin_name,
                                        discovered_service.description)
            section_name = cmk.base.check_utils.section_name_of(
                discovered_service.check_plugin_name)

            try:
                try:
                    section_content = multi_host_sections.get_section_content(hostname,
                                                                              ipaddress,
                                                                              section_name,
                                                                              for_discovery=True)
                except MKParseFunctionError as e:
                    if cmk.utils.debug.enabled() or on_error == "raise":
                        x = e.exc_info()
                        # re-raise the original exception to not destory the trace. This may raise a MKCounterWrapped
                        # exception which need to lead to a skipped check instead of a crash
                        # TODO CMK-3729, PEP-3109
                        new_exception = x[0](x[1])
                        new_exception.__traceback__ = x[2]  # type: ignore[attr-defined]
                        raise new_exception
                    raise
            except Exception as e:
                if cmk.utils.debug.enabled():
                    raise
                exitcode = 3
                output = u"Error: %s" % e

            # TODO: Move this to a helper function
            if section_content is None:  # No data for this check type
                exitcode = 3
                output = u"Received no data"

            if not section_content and cmk.base.check_utils.is_snmp_check(discovered_service.check_plugin_name) \
               and not config.check_info[discovered_service.check_plugin_name]["handle_empty_info"]:
                exitcode = 0
                output = u"Received no data"

            item_state.set_item_state_prefix(discovered_service.check_plugin_name,
                                             discovered_service.item)

            if exitcode is None:
                check_function = config.check_info[
                    discovered_service.check_plugin_name]["check_function"]
                if check_source != 'manual':
                    params = check_table.get_precompiled_check_parameters(
                        hostname, discovered_service.item,
                        config.compute_check_parameters(hostname,
                                                        discovered_service.check_plugin_name,
                                                        discovered_service.item, params),
                        discovered_service.check_plugin_name)
                else:
                    params = check_table.get_precompiled_check_parameters(
                        hostname, discovered_service.item, params,
                        discovered_service.check_plugin_name)

                try:
                    item_state.reset_wrapped_counters()
                    exitcode, output, perfdata = checking.sanitize_check_result(
                        check_function(discovered_service.item,
                                       checking.determine_check_params(params), section_content),
                        cmk.base.check_utils.is_snmp_check(discovered_service.check_plugin_name),
                    )
                    item_state.raise_counter_wrap()
                except item_state.MKCounterWrapped:
                    output = u"WAITING - Counter based check, cannot be done offline"
                except Exception:
                    if cmk.utils.debug.enabled():
                        raise
                    exitcode = 3
                    output = u"UNKNOWN - invalid output from agent or error in check implementation"
        else:
            exitcode = None
            output = u"WAITING - %s check, cannot be done offline" % check_source.title()
            perfdata = []

        if check_source == "active":
            params = _get_check_parameters(discovered_service)

        checkgroup = None  # type: Optional[RulesetName]
        if check_source in ["legacy", "active", "custom"]:
            checkgroup = None
            if config.service_ignored(hostname, None, discovered_service.description):
                check_source = "%s_ignored" % check_source
        else:
            checkgroup = config.check_info[discovered_service.check_plugin_name]["group"]

        if isinstance(params, config.TimespecificParamList):
            params = {
                "tp_computed_params": {
                    "params": checking.determine_check_params(params),
                    "computed_at": time.time(),
                }
            }

        table.append((check_source, discovered_service.check_plugin_name, checkgroup,
                      discovered_service.item, discovered_service.parameters_unresolved, params,
                      discovered_service.description, exitcode, output, perfdata,
                      discovered_service.service_labels.to_dict()))

    return table, discovered_host_labels


def _get_check_parameters(discovered_service):
    # type: (DiscoveredService) -> CheckParameters
    """Retrieves the check parameters (read from autochecks), possibly resolving a
    string to its actual value."""
    params = discovered_service.parameters_unresolved
    if not isinstance(params, str):
        return params
    check_context = config.get_check_context(discovered_service.check_plugin_name)
    # TODO: Can't we simply access check_context[paramstring]?
    return eval(params, check_context, check_context)
