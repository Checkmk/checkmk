#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import os
import socket
import time
import signal
from typing import Union, Iterator, Callable, List, Text, Optional, Dict, Tuple  # pylint: disable=unused-import
from pathlib2 import Path

from cmk.utils.regex import regex
import cmk.utils.tty as tty
import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException, MKTimeout
import cmk.utils.store as store

import cmk_base.crash_reporting
import cmk_base.config as config
import cmk_base.console as console
import cmk_base.ip_lookup as ip_lookup
import cmk_base.check_api_utils as check_api_utils
import cmk_base.item_state as item_state
import cmk_base.checking as checking
import cmk_base.data_sources as data_sources
import cmk_base.check_table as check_table
import cmk_base.core
from cmk_base.exceptions import MKParseFunctionError
import cmk_base.cleanup
import cmk_base.check_utils
import cmk_base.decorator
import cmk_base.snmp_scan as snmp_scan

# Run the discovery queued by check_discovery() - if any
_marked_host_discovery_timeout = 120

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


class DiscoveredService(object):
    __slots__ = ["_check_plugin_name", "_item", "_description", "_paramstr"]

    def __init__(self, check_plugin_name, item, description, paramstr):
        # type: (check_table.CheckPluginName, check_table.Item, Text, str) -> None
        self._check_plugin_name = check_plugin_name
        self._item = item
        self._description = description
        self._paramstr = paramstr

    @property
    def check_plugin_name(self):
        return self._check_plugin_name

    @property
    def item(self):
        return self._item

    @property
    def description(self):
        return self._description

    @property
    def paramstr(self):
        return self._paramstr

    def __eq__(self, other):
        """Is used during service discovery list computation to detect and replace duplicates
        For this the paramstr needs to be ignored."""
        return self.check_plugin_name == other.check_plugin_name and self.item == other.item

    def __hash__(self):
        """Is used during service discovery list computation to detect and replace duplicates
        For this the paramstr needs to be ignored."""
        return hash((self.check_plugin_name, self.item))


DiscoveredServicesTable = Dict[Tuple[check_table.CheckPluginName, check_table.
                                     Item], Tuple[str, DiscoveredService]]


# Function implementing cmk -I and cmk -II. This is directly
# being called from the main option parsing code. The list of
# hostnames is already prepared by the main code. If it is
# empty then we use all hosts and switch to using cache files.
def do_discovery(hostnames, check_plugin_names, only_new):
    config_cache = config.get_config_cache()
    use_caches = data_sources.abstract.DataSource.get_may_use_cache_file()
    if not hostnames:
        console.verbose("Discovering services on all hosts\n")
        hostnames = config_cache.all_active_realhosts()
        use_caches = True
    else:
        console.verbose("Discovering services on: %s\n" % ", ".join(hostnames))

    # For clusters add their nodes to the list. Clusters itself
    # cannot be discovered but the user is allowed to specify
    # them and we do discovery on the nodes instead.
    cluster_hosts = []
    for h in hostnames:
        host_config = config_cache.get_host_config(h)
        if host_config.is_cluster:
            cluster_hosts.append(h)
            hostnames += host_config.nodes

    # Then remove clusters and make list unique
    hostnames = list(set([h for h in hostnames if not config_cache.get_host_config(h).is_cluster]))
    hostnames.sort()

    # Now loop through all hosts
    for hostname in hostnames:
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
            do_snmp_scan = not use_caches or not _has_autochecks(hostname)

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
            cmk_base.cleanup.cleanup_globals()

    # Check whether or not the cluster host autocheck files are still
    # existant. Remove them. The autochecks are only stored in the nodes
    # autochecks files these days.
    for hostname in cluster_hosts:
        _remove_autochecks_file(hostname)


def _do_discovery_for(hostname, ipaddress, sources, multi_host_sections, check_plugin_names,
                      only_new, on_error):
    # type: (str, Optional[str], data_sources.DataSources, data_sources.MultiHostSections, List[check_table.CheckPluginName], bool, str) -> None
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
    discovered_services = _discover_services(hostname,
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

    result = []  # type: List[DiscoveredService]

    if not check_plugin_names and not only_new:
        existing_services = []  # type: List[DiscoveredService]
    else:
        existing_services = parse_autochecks_file(hostname)

    # Parse old items into a dict (ct, item) -> paramstring
    for existing_service in existing_services:
        # Take over old items if -I is selected or if -II
        # is selected with --checks= and the check type is not
        # one of the listed ones
        if only_new or (check_plugin_names and
                        existing_service.check_plugin_name not in check_plugin_names):
            result.append(existing_service)

    services_per_plugin = {}  # type: Dict[check_table.CheckPluginName, int]
    for discovered_service in discovered_services:
        if discovered_service not in result:
            result.append(discovered_service)
            services_per_plugin.setdefault(discovered_service.check_plugin_name, 0)
            services_per_plugin[discovered_service.check_plugin_name] += 1

    _save_autochecks_file(hostname, result)

    if services_per_plugin:
        for check_plugin_name, count in sorted(services_per_plugin.items()):
            console.verbose("%s%3d%s %s\n" %
                            (tty.green + tty.bold, count, tty.normal, check_plugin_name))
        console.section_success("Found %d services" % sum(services_per_plugin.values()))
    else:
        console.section_success("Found nothing%s" % (only_new and " new" or ""))


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
        "clustered_new": 0,
        "clustered_vanished": 0,
    }

    if hostname not in config_cache.all_active_realhosts():
        return counts, ""

    if service_filter is None:
        service_filter = lambda hostname, check_plugin_name, item: True

    err = None

    try:
        # in "refresh" mode we first need to remove all previously discovered
        # checks of the host, so that _get_host_services() does show us the
        # new discovered check parameters.
        if mode == "refresh":
            counts["self_removed"] += remove_autochecks_of(host_config)  # this is cluster-aware!

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
        services = _get_host_services(host_config,
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
        set_autochecks_of(host_config, new_items)

    except MKTimeout:
        raise  # let general timeout through

    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        err = str(e)

    counts["self_total"] = counts["self_new"] + counts["self_kept"]
    return counts, err


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


@cmk_base.decorator.handle_check_mk_check_result("discovery", "Check_MK Discovery")
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

    services = _get_host_services(host_config,
                                  ipaddress,
                                  sources,
                                  multi_host_sections,
                                  on_error="raise")

    need_rediscovery = False

    params_rediscovery = params.get("inventory_rediscovery", {})

    item_filters = None  # type: Optional[Callable]
    if params_rediscovery.get("service_whitelist", []) or\
            params_rediscovery.get("service_blacklist", []):
        # whitelist. if none is specified, this matches everything
        whitelist = regex("|".join(
            ["(%s)" % pat for pat in params_rediscovery.get("service_whitelist", [".*"])]))
        # blacklist. if none is specified, this matches nothing
        blacklist = regex("|".join(
            ["(%s)" % pat for pat in params_rediscovery.get("service_blacklist", ["(?!x)x"])]))

        item_filters = lambda hostname, check_plugin_name, item:\
                _discovery_filter_by_lists(hostname, check_plugin_name, item, whitelist, blacklist)

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

                if not unfiltered and\
                        (item_filters is None or item_filters(hostname, discovered_service.check_plugin_name, discovered_service.item)):
                    unfiltered = True

                long_infotexts.append(
                    u"%s: %s: %s" %
                    (title, discovered_service.check_plugin_name, discovered_service.description))

        if affected_check_plugin_names:
            info = ", ".join(["%s:%d" % e for e in affected_check_plugin_names.items()])
            st = params.get(params_key, default_state)
            status = cmk_base.utils.worst_service_state(status, st)
            infotexts.append(u"%d %s services (%s)%s" %
                             (count, title, info, check_api_utils.state_markers[st]))

            if params.get("inventory_rediscovery", False):
                mode = params["inventory_rediscovery"]["mode"]
                if unfiltered and\
                        ((check_state == "new"      and mode in ( 0, 2, 3 )) or
                         (check_state == "vanished" and mode in ( 1, 2, 3 ))):
                    need_rediscovery = True
        else:
            infotexts.append(u"no %s services found" % title)

    for check_source, discovered_service in services.values():
        if check_source == "ignored":
            long_infotexts.append(
                u"ignored: %s: %s" %
                (discovered_service.check_plugin_name, discovered_service.description))

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
    def touch(filename):
        if not os.path.exists(filename):
            f = open(filename, "w")
            f.close()

    autodiscovery_dir = cmk.utils.paths.var_dir + '/autodiscovery'
    discovery_filename = os.path.join(autodiscovery_dir, hostname)

    if not os.path.exists(autodiscovery_dir):
        os.makedirs(autodiscovery_dir)
    touch(discovery_filename)


class DiscoveryTimeout(Exception):
    pass


def _handle_discovery_timeout():
    raise DiscoveryTimeout()


def _set_discovery_timeout():
    signal.signal(signal.SIGALRM, _handle_discovery_timeout)
    # Add an additional 10 seconds as grace period
    signal.alarm(_marked_host_discovery_timeout + 10)


def _clear_discovery_timeout():
    signal.alarm(0)


def _get_autodiscovery_dir():
    return cmk.utils.paths.var_dir + '/autodiscovery'


def discover_marked_hosts(core):
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
        if config.monitoring_core == "cmc":
            cmk_base.core.do_reload(core)
        else:
            cmk_base.core.do_restart(core)


def _fetch_host_states():
    host_states = {}
    try:
        import livestatus
        query = "GET hosts\nColumns: name state"
        host_states = dict(livestatus.LocalConnection().query(query))
    except (livestatus.MKLivestatusNotFoundError, livestatus.MKLivestatusSocketError):
        pass
    return host_states


def _discover_marked_host_exists(config_cache, hostname):
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
    hostname = host_config.hostname
    services_changed = False

    mode_table = {0: "new", 1: "remove", 2: "fixall", 3: "refresh"}

    console.verbose("%s%s%s:\n" % (tty.bold, hostname, tty.normal))
    host_flag_path = os.path.join(_get_autodiscovery_dir(), hostname)

    params = host_config.discovery_check_parameters
    params_rediscovery = params.get("inventory_rediscovery", {})
    if "service_blacklist" in params_rediscovery or "service_whitelist" in params_rediscovery:
        # whitelist. if none is specified, this matches everything
        whitelist = regex("|".join(
            ["(%s)" % pat for pat in params_rediscovery.get("service_whitelist", [".*"])]))
        # blacklist. if none is specified, this matches nothing
        blacklist = regex("|".join(
            ["(%s)" % pat for pat in params_rediscovery.get("service_blacklist", ["(?!x)x"])]))
        item_filters = lambda hostname, check_plugin_name, item:\
            _discovery_filter_by_lists(hostname, check_plugin_name, item, whitelist, blacklist)
    else:
        item_filters = None

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
               result["clustered_vanished"] == 0:
                console.verbose("  nothing changed.\n")
            else:
                console.verbose("  %(self_new)s new, %(self_removed)s removed, "\
                                "%(self_kept)s kept, %(self_total)s total services. "\
                                "clustered new %(clustered_new)s, clustered vanished %(clustered_vanished)s" % result)

                # Note: Even if the actual mark-for-discovery flag may have been created by a cluster host,
                #       the activation decision is based on the discovery configuration of the node
                if redisc_params["activation"]:
                    services_changed = True

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

    return services_changed


def _queue_age():
    autodiscovery_dir = _get_autodiscovery_dir()
    oldest = time.time()
    for filename in os.listdir(autodiscovery_dir):
        oldest = min(oldest, os.path.getmtime(autodiscovery_dir + "/" + filename))
    return oldest


def _may_rediscover(params, now_ts, oldest_queued):
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


def _discovery_filter_by_lists(hostname, check_plugin_name, item, whitelist, blacklist):
    description = config.service_description(hostname, check_plugin_name, item)
    return whitelist.match(description) is not None and\
        blacklist.match(description) is None


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

        s.send("COMMAND [%d] %s\n" % (now, command))
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
    # type: (str, Optional[str], data_sources.DataSources, data_sources.MultiHostSections, str) -> List[DiscoveredService]
    # Set host name for host_name()-function (part of the Check API)
    # (used e.g. by ps-discovery)
    check_api_utils.set_hostname(hostname)

    discovered_services = []  # type: List[DiscoveredService]
    try:
        for check_plugin_name in sources.get_check_plugin_names():
            try:
                discovered_services += list(
                    _execute_discovery(multi_host_sections, hostname, ipaddress, check_plugin_name,
                                       on_error))
            except (KeyboardInterrupt, MKTimeout):
                raise
            except Exception as e:
                if on_error == "raise":
                    raise
                elif on_error == "warn":
                    console.error("Discovery of '%s' failed: %s\n" % (check_plugin_name, e))

        check_table_formatted = {}  # type: check_table.CheckTable
        for discovered_service in discovered_services:
            check_table_formatted[(discovered_service.check_plugin_name,
                                   discovered_service.item)] = (None,
                                                                discovered_service.description, [])

        check_table_formatted = check_table.remove_duplicate_checks(check_table_formatted)
        for discovered_service in discovered_services[:]:
            if (discovered_service.check_plugin_name,
                    discovered_service.item) not in check_table_formatted:
                discovered_services.remove(discovered_service)

        return discovered_services

    except KeyboardInterrupt:
        raise MKGeneralException("Interrupted by Ctrl-C.")


def _get_sources_for_discovery(hostname, ipaddress, check_plugin_names, do_snmp_scan, on_error):
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
    max_cachefile_age = config.inventory_max_cachefile_age if use_caches else 0
    return sources.get_host_sections(max_cachefile_age)


def _execute_discovery(multi_host_sections, hostname, ipaddress, check_plugin_name, on_error):
    # type: (data_sources.MultiHostSections, str, Optional[str], str, str) -> Iterator[DiscoveredService]
    # Skip this check type if is ignored for that host
    if config.service_ignored(hostname, check_plugin_name, None):
        console.vverbose("  Skip ignored check plugin name '%s'\n" % check_plugin_name)
        return

    discovery_function = _get_discovery_function_of(check_plugin_name)

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
                else:
                    # re-raise the original exception to not destory the trace. This may raise a MKCounterWrapped
                    # exception which need to lead to a skipped check instead of a crash
                    raise x[0], x[1], x[2]

            elif on_error == "warn":
                section_name = cmk_base.check_utils.section_name_of(check_plugin_name)
                console.warning("Exception while parsing agent section '%s': %s\n" %
                                (section_name, e))

            return

        if section_content is None:  # No data for this check type
            return

        # In case of SNMP checks but missing agent response, skip this check.
        # Special checks which still need to be called even with empty data
        # may declare this.
        if not section_content and cmk_base.check_utils.is_snmp_check(check_plugin_name) \
           and not config.check_info[check_plugin_name]["handle_empty_info"]:
            return

        # Now do the actual discovery
        discovered_items = _execute_discovery_function(discovery_function, section_content)
        for discovered_service in _validate_discovered_items(hostname, check_plugin_name,
                                                             discovered_items):
            yield discovered_service
    except Exception as e:
        if on_error == "warn":
            console.warning("  Exception in discovery function of check type '%s': %s" %
                            (check_plugin_name, e))
        elif on_error == "raise":
            raise


def _get_discovery_function_of(check_plugin_name):
    try:
        discovery_function = config.check_info[check_plugin_name]["inventory_function"]
    except KeyError:
        raise MKGeneralException("No such check type '%s'" % check_plugin_name)

    if discovery_function is None:
        return lambda _info: _no_discovery_possible(check_plugin_name)

    return discovery_function


def _no_discovery_possible(check_plugin_name):
    console.verbose("%s does not support discovery. Skipping it.\n", check_plugin_name)
    return []


def _execute_discovery_function(discovery_function, section_content):
    discovered_items = discovery_function(section_content)

    # tolerate function not explicitely returning []
    if discovered_items is None:
        discovered_items = []

    # New yield based api style
    elif not isinstance(discovered_items, list):
        discovered_items = list(discovered_items)

    return discovered_items


def _validate_discovered_items(hostname, check_plugin_name, discovered_items):
    # type: (str, check_table.CheckPluginName, List) -> Iterator[DiscoveredService]
    for entry in discovered_items:
        if not isinstance(entry, tuple):
            console.error("%s: Check %s returned invalid discovery data (entry not a tuple): %r\n" %
                          (hostname, check_plugin_name, repr(entry)))
            continue

        if len(entry) == 2:  # comment is now obsolete
            item, paramstring = entry
        elif len(entry) == 3:  # allow old school
            item, __, paramstring = entry
        else:  # we really don't want longer tuples (or 1-tuples).
            console.error(
                "%s: Check %s returned invalid discovery data (not 2 or 3 elements): %r\n" %
                (hostname, check_plugin_name, repr(entry)))
            continue

        # Check_MK 1.2.7i3 defines items to be unicode strings. Convert non unicode
        # strings here seamless. TODO remove this conversion one day and replace it
        # with a validation that item needs to be of type unicode
        if isinstance(item, str):
            item = config.decode_incoming_string(item)

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
            paramstr=paramstring,
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
    # type: (config.HostConfig, Optional[str], data_sources.DataSources, data_sources.MultiHostSections, str) -> DiscoveredServicesTable
    if host_config.is_cluster:
        return _get_cluster_services(host_config, ipaddress, sources, multi_host_sections, on_error)

    return _get_node_services(host_config, ipaddress, sources, multi_host_sections, on_error)


# Do the actual work for a non-cluster host or node
def _get_node_services(host_config, ipaddress, sources, multi_host_sections, on_error):
    # type: (config.HostConfig, Optional[str], data_sources.DataSources, data_sources.MultiHostSections, str) -> DiscoveredServicesTable
    hostname = host_config.hostname
    services = _get_discovered_services(hostname, ipaddress, sources, multi_host_sections, on_error)

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

    return _merge_manual_services(host_config, services, on_error)


# Part of _get_node_services that deals with discovered services
def _get_discovered_services(hostname, ipaddress, sources, multi_host_sections, on_error):
    # type: (str, Optional[str], data_sources.DataSources, data_sources.MultiHostSections, str) -> DiscoveredServicesTable
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
    discovered_services = _discover_services(hostname, ipaddress, sources, multi_host_sections,
                                             on_error)
    for discovered_service in discovered_services:
        services.setdefault((discovered_service.check_plugin_name, discovered_service.item),
                            ("new", discovered_service))

    # Match with existing items -> "old" and "vanished"
    for existing_service in parse_autochecks_file(hostname):
        table_id = existing_service.check_plugin_name, existing_service.item
        check_source = "vanished" if table_id not in services else "old"
        services[table_id] = check_source, existing_service

    return services


# TODO: Rename or extract disabled services handling
def _merge_manual_services(host_config, services, on_error):
    # type: (config.HostConfig, DiscoveredServicesTable, str) -> DiscoveredServicesTable
    """Add/replace manual and active checks and handle ignoration"""
    hostname = host_config.hostname

    # Find manual checks. These can override discovered checks -> "manual"
    manual_items = check_table.get_check_table(hostname, skip_autochecks=True)
    for (check_plugin_name, item), (params, descr, _unused_deps) in manual_items.items():
        # TODO: Reduce this duplication
        try:
            description = config.service_description(hostname, check_plugin_name, item)
        except Exception as e:
            if on_error == "raise":
                raise
            elif on_error == "warn":
                console.error("Invalid service description: %s\n" % e)
            else:
                continue  # ignore

        services[(check_plugin_name, item)] = ('manual',
                                               DiscoveredService(check_plugin_name, item,
                                                                 description, repr(params)))

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
    # type: (config.HostConfig, Optional[str], data_sources.DataSources, data_sources.MultiHostSections, str) -> DiscoveredServicesTable
    config_cache = config.get_config_cache()

    # Get setting from cluster SNMP data source
    do_snmp_scan = False
    for source in sources.get_data_sources():
        if isinstance(source, data_sources.SNMPDataSource):
            do_snmp_scan = source.get_do_snmp_scan()

    cluster_items = {}  # type: DiscoveredServicesTable
    if not host_config.nodes:
        return cluster_items

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

        services = _get_discovered_services(node, node_ipaddress, node_sources, multi_host_sections,
                                            on_error)
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
    return _merge_manual_services(host_config, cluster_items, on_error)


def resolve_paramstring(check_plugin_name, paramstring):
    # type: (str, str) -> check_table.CheckParameters
    """Translates a parameter string (read from autochecks) to it's final value
    (according to the current configuration)"""
    check_context = config.get_check_context(check_plugin_name)
    # TODO: Can't we simply access check_context[paramstring]?
    return eval(paramstring, check_context, check_context)


# TODO: Can't we reduce the duplicate code here? Check out the "checking" code
def get_check_preview(hostname, use_caches, do_snmp_scan, on_error):
    # type: (str, bool, bool, str) -> List[Tuple[str, str, Optional[str], check_table.Item, str, check_table.CheckParameters, Text, Optional[int], Text, List[Tuple]]]
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

    services = _get_host_services(host_config, ipaddress, sources, multi_host_sections, on_error)

    table = []
    for check_source, discovered_service in services.values():
        params = None
        exitcode = None
        perfdata = []  # type: List[Tuple]
        if check_source not in ['legacy', 'active', 'custom']:
            # apply check_parameters
            try:
                if isinstance(discovered_service.paramstr, str):
                    params = resolve_paramstring(discovered_service.check_plugin_name,
                                                 discovered_service.paramstr)
                else:
                    params = discovered_service.paramstr
            except Exception:
                raise MKGeneralException("Invalid check parameter string '%s'" %
                                         discovered_service.paramstr)

            check_api_utils.set_service(discovered_service.check_plugin_name,
                                        discovered_service.description)
            section_name = cmk_base.check_utils.section_name_of(
                discovered_service.check_plugin_name)

            if discovered_service.check_plugin_name not in config.check_info:
                continue  # Skip not existing check silently

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
                        raise x[0], x[1], x[2]
                    else:
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

            if not section_content and cmk_base.check_utils.is_snmp_check(discovered_service.check_plugin_name) \
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
                    result = checking.sanitize_check_result(
                        check_function(discovered_service.item,
                                       checking.determine_check_params(params), section_content),
                        cmk_base.check_utils.is_snmp_check(discovered_service.check_plugin_name))
                    item_state.raise_counter_wrap()
                except item_state.MKCounterWrapped as e:
                    result = (None, u"WAITING - Counter based check, cannot be done offline")
                except Exception as e:
                    if cmk.utils.debug.enabled():
                        raise
                    result = (
                        3, u"UNKNOWN - invalid output from agent or error in check implementation")
                if len(result) == 2:
                    result = (result[0], result[1], [])
                exitcode, output, perfdata = result
        else:
            exitcode = None
            output = u"WAITING - %s check, cannot be done offline" % check_source.title()
            perfdata = []

        if check_source == "active":
            params = resolve_paramstring(discovered_service.check_plugin_name,
                                         discovered_service.paramstr)

        if check_source in ["legacy", "active", "custom"]:
            checkgroup = None
            if config.service_ignored(hostname, None, discovered_service.description):
                check_source = "%s_ignored" % check_source
        else:
            checkgroup = config.check_info[discovered_service.check_plugin_name]["group"]

        table.append((check_source, discovered_service.check_plugin_name, checkgroup,
                      discovered_service.item, discovered_service.paramstr, params,
                      discovered_service.description, exitcode, output, perfdata))

    return table


#.
#   .--Autochecks----------------------------------------------------------.
#   |            _         _             _               _                 |
#   |           / \  _   _| |_ ___   ___| |__   ___  ___| | _____          |
#   |          / _ \| | | | __/ _ \ / __| '_ \ / _ \/ __| |/ / __|         |
#   |         / ___ \ |_| | || (_) | (__| | | |  __/ (__|   <\__ \         |
#   |        /_/   \_\__,_|\__\___/ \___|_| |_|\___|\___|_|\_\___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Reading, parsing, writing, modifying autochecks files               |
#   '----------------------------------------------------------------------'


# TODO: use store.load_data_from_file()
# TODO: External call sites!
def parse_autochecks_file(hostname):
    # type: (str) -> List[DiscoveredService]
    """Read autochecks, but do not compute final check parameters"""
    def split_python_tuple(line):
        quote = None
        bracklev = 0
        backslash = False
        for i, c in enumerate(line):
            if backslash:
                backslash = False
                continue
            elif c == '\\':
                backslash = True
            elif c == quote:
                quote = None  # end of quoted string
            elif c in ['"', "'"] and not quote:
                quote = c  # begin of quoted string
            elif quote:
                continue
            elif c in ['(', '{', '[']:
                bracklev += 1
            elif c in [')', '}', ']']:
                bracklev -= 1
            elif bracklev > 0:
                continue
            elif c == ',':
                value = line[0:i]
                rest = line[i + 1:]
                return value.strip(), rest

        return line.strip(), None

    path = "%s/%s.mk" % (cmk.utils.paths.autochecks_dir, hostname)
    if not os.path.exists(path):
        return []

    lineno = 0
    services = []  # type: List[DiscoveredService]
    for line in file(path):
        lineno += 1
        try:
            line = line.strip()
            if not line.startswith("("):
                continue

            # drop everything after potential '#' (from older versions)
            i = line.rfind('#')
            if i > 0:  # make sure # is not contained in string
                rest = line[i:]
                if '"' not in rest and "'" not in rest:
                    line = line[:i].strip()

            if line.endswith(","):
                line = line[:-1]
            line = line[1:-1]  # drop brackets

            # First try old format - with hostname
            parts = []
            while True:
                try:
                    part, line = split_python_tuple(line)
                    parts.append(part)
                except:
                    break
            if len(parts) == 4:
                parts = parts[1:]  # drop hostname, legacy format with host in first column
            elif len(parts) != 3:
                raise Exception("Invalid number of parts: %d (%r)" % (len(parts), parts))

            checktypestring, itemstring, paramstring = parts

            item = eval(itemstring)
            # With Check_MK 1.2.7i3 items are now defined to be unicode strings. Convert
            # items from existing autocheck files for compatibility. TODO remove this one day
            if isinstance(item, str):
                item = config.decode_incoming_string(item)

            check_plugin_name = eval(checktypestring)
        except:
            if cmk.utils.debug.enabled():
                raise
            raise Exception("Invalid line %d in autochecks file %s" % (lineno, path))

        try:
            description = config.service_description(hostname, check_plugin_name, item)
        except Exception:
            continue  # ignore

        services.append(DiscoveredService(check_plugin_name, item, description, paramstring))

    return services


def _has_autochecks(hostname):
    # type: (str) -> bool
    return os.path.exists(cmk.utils.paths.autochecks_dir + "/" + hostname + ".mk")


def _remove_autochecks_file(hostname):
    # type: (str) -> None
    filepath = cmk.utils.paths.autochecks_dir + "/" + hostname + ".mk"
    try:
        os.remove(filepath)
    except OSError:
        pass


def _save_autochecks_file(hostname, items):
    # type: (str, List[DiscoveredService]) -> None
    if not os.path.exists(cmk.utils.paths.autochecks_dir):
        os.makedirs(cmk.utils.paths.autochecks_dir)

    filepath = Path(cmk.utils.paths.autochecks_dir) / ("%s.mk" % hostname)
    content = []
    content.append("[")
    for discovered_service in sorted(items, key=lambda s: (s.check_plugin_name, s.item)):
        content.append("  (%r, %r, %s)," % (discovered_service.check_plugin_name,
                                            discovered_service.item, discovered_service.paramstr))
    content.append("]\n")
    store.save_file(str(filepath), "\n".join(content))


def set_autochecks_of(host_config, new_items):
    # type: (config.HostConfig, List[DiscoveredService]) -> None
    """Merge existing autochecks with the given autochecks for a host and save it"""
    if host_config.is_cluster:
        _set_autochecks_of_cluster(host_config, new_items)
    else:
        _set_autochecks_of_real_hosts(host_config, new_items)


def _set_autochecks_of_real_hosts(host_config, new_items):
    # type: (config.HostConfig, List[DiscoveredService]) -> None
    new_autochecks = []  # type: List[DiscoveredService]

    # write new autochecks file, but take paramstrings from existing ones
    # for those checks which are kept
    for existing_service in parse_autochecks_file(host_config.hostname):
        # TODO: Need to implement a list class that realizes in / not in correctly
        if existing_service in new_items:
            new_autochecks.append(existing_service)

    for discovered_service in new_items:
        if discovered_service not in new_autochecks:
            new_autochecks.append(discovered_service)

    # write new autochecks file for that host
    _save_autochecks_file(host_config.hostname, new_autochecks)


def _set_autochecks_of_cluster(host_config, new_items):
    # type: (config.HostConfig, List[DiscoveredService]) -> None
    """A Cluster does not have an autochecks file. All of its services are located
    in the nodes instead. For clusters we cycle through all nodes remove all
    clustered service and add the ones we've got as input."""
    if not host_config.nodes:
        return

    config_cache = config.get_config_cache()

    new_autochecks = []  # type: List[DiscoveredService]
    for node in host_config.nodes:
        for existing_service in parse_autochecks_file(node):
            if host_config.hostname != config_cache.host_of_clustered_service(
                    node, existing_service.description):
                new_autochecks.append(existing_service)

        for discovered_service in new_items:
            new_autochecks.append(discovered_service)

        # write new autochecks file for that host
        _save_autochecks_file(node, new_autochecks)

    # Check whether or not the cluster host autocheck files are still existant.
    # Remove them. The autochecks are only stored in the nodes autochecks files
    # these days.
    _remove_autochecks_file(host_config.hostname)


def remove_autochecks_of(host_config):
    # type: (config.HostConfig) -> int
    """Remove all autochecks of a host while being cluster-aware!"""
    removed = 0
    if host_config.nodes:
        for node_name in host_config.nodes:
            removed += _remove_autochecks_of_host(node_name)
    else:
        removed += _remove_autochecks_of_host(host_config.hostname)

    return removed


def _remove_autochecks_of_host(hostname):
    # type: (str) -> int
    removed = 0
    new_items = []  # type: List[DiscoveredService]
    config_cache = config.get_config_cache()

    old_items = parse_autochecks_file(hostname)
    for existing_service in old_items:
        if hostname != config_cache.host_of_clustered_service(hostname,
                                                              existing_service.description):
            new_items.append(existing_service)
        else:
            removed += 1
    _save_autochecks_file(hostname, new_items)
    return removed
