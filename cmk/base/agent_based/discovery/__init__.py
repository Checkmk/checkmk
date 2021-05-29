#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import suppress
import itertools
from pathlib import Path
import socket
import time
from typing import (
    Callable,
    Container,
    Counter,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

import livestatus

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.caching import config_cache as _config_cache
from cmk.utils.check_utils import ActiveCheckResult, worst_service_state, wrap_parameters
from cmk.utils.exceptions import MKGeneralException, MKTimeout, OnError
from cmk.utils.log import console
from cmk.utils.object_diff import make_object_diff
from cmk.utils.type_defs import (
    CheckPluginName,
    CheckPluginNameStr,
    DiscoveryResult,
    EVERYTHING,
    HostAddress,
    HostName,
    Item,
    MetricTuple,
    RulesetName,
    state_markers,
)

import cmk.core_helpers.cache
from cmk.core_helpers.protocol import FetcherMessage
from cmk.core_helpers.type_defs import Mode, NO_SELECTION, SectionNameCollection

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.agent_based.decorator as decorator
import cmk.base.autochecks as autochecks
import cmk.base.check_table as check_table
import cmk.base.check_utils
import cmk.base.agent_based.checking as checking
import cmk.base.config as config
import cmk.base.core
import cmk.base.crash_reporting
import cmk.base.section as section
from cmk.base.agent_based.data_provider import make_broker, ParsedSectionsBroker
from cmk.base.agent_based.utils import check_sources, check_parsing_errors
from cmk.base.api.agent_based import checking_classes
from cmk.base.api.agent_based.value_store import load_host_value_store, ValueStoreManager
from cmk.base.api.agent_based.type_defs import Parameters
from cmk.base.check_utils import LegacyCheckParameters, Service, ServiceID
from cmk.base.core_config import MonitoringCore
from cmk.base.discovered_labels import HostLabel

from ._discovered_services import analyse_discovered_services
from ._filters import ServiceFilters as _ServiceFilters
from ._host_labels import analyse_host_labels, analyse_node_labels
from .utils import DiscoveryMode, TimeLimitFilter, QualifiedDiscovery

ServicesTableEntry = Tuple[str, Service, List[HostName]]
ServicesTable = Dict[ServiceID, ServicesTableEntry]
ServicesByTransition = Dict[str, List[autochecks.ServiceWithNodes]]

CheckPreviewEntry = Tuple[str, CheckPluginNameStr, Optional[RulesetName], Item,
                          LegacyCheckParameters, LegacyCheckParameters, str, Optional[int], str,
                          List[MetricTuple], Dict[str, str], List[HostName]]
CheckPreviewTable = List[CheckPreviewEntry]

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
    now = int(time.time())
    service = ("Check_MK Discovery"
               if 'cmk_inventory' in config.use_new_descriptions_for else "Check_MK inventory")
    # Ignore missing check and avoid warning in cmc.log
    cmc_try = ";TRY" if config.monitoring_core == "cmc" else ""
    command = f"SCHEDULE_FORCED_SVC_CHECK;{host_name};{service};{now}{cmc_try}"

    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(cmk.utils.paths.livestatus_unix_socket)
        s.send(f"COMMAND [{now}] {command}\n".encode())
    except Exception:
        if cmk.utils.debug.enabled():
            raise


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


def commandline_discovery(
    arg_hostnames: Set[HostName],
    *,
    selected_sections: SectionNameCollection,
    run_plugin_names: Container[CheckPluginName],
    arg_only_new: bool,
    only_host_labels: bool = False,
) -> None:
    """Implementing cmk -I and cmk -II

    This is directly called from the main option parsing code.
    The list of hostnames is already prepared by the main code.
    If it is empty then we use all hosts and switch to using cache files.
    """
    config_cache = config.get_config_cache()

    on_error = OnError.RAISE if cmk.utils.debug.enabled() else OnError.WARN

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
                file_cache_max_age=config.max_cachefile_age(),
                fetcher_messages=(),
                force_snmp_cache_refresh=False,
                on_scan_error=on_error,
            )
            _commandline_discovery_on_host(
                host_name,
                ipaddress,
                parsed_sections_broker,
                run_plugin_names,
                arg_only_new,
                load_labels=arg_only_new,
                only_host_labels=only_host_labels,
                on_error=on_error,
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


def _commandline_discovery_on_host(
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    parsed_sections_broker: ParsedSectionsBroker,
    run_plugin_names: Container[CheckPluginName],
    only_new: bool,
    *,
    load_labels: bool,
    only_host_labels: bool,
    on_error: OnError,
) -> None:

    section.section_step("Analyse discovered host labels")

    host_labels = analyse_node_labels(
        host_name=host_name,
        ipaddress=ipaddress,
        parsed_sections_broker=parsed_sections_broker,
        load_labels=load_labels,
        save_labels=True,
        on_error=on_error,
    )

    count = len(host_labels.new) if host_labels.new else ("no new" if only_new else "no")
    section.section_success(f"Found {count} host labels")

    if only_host_labels:
        return

    section.section_step("Analyse discovered services")

    service_result = analyse_discovered_services(
        host_name=host_name,
        ipaddress=ipaddress,
        parsed_sections_broker=parsed_sections_broker,
        run_plugin_names=run_plugin_names,
        only_new=only_new,
        on_error=on_error,
    )

    # TODO (mo): for the labels the corresponding code is in _host_labels.
    # We should put the persisting in one place.
    autochecks.save_autochecks_file(host_name, service_result.present)

    new_per_plugin = Counter(s.check_plugin_name for s in service_result.new)
    for name, count in sorted(new_per_plugin.items()):
        console.verbose("%s%3d%s %s\n" % (tty.green + tty.bold, count, tty.normal, name))

    count = len(service_result.new) if service_result.new else ("no new" if only_new else "no")
    section.section_success(f"Found {count} services")

    for detail in check_parsing_errors(parsed_sections_broker.parsing_errors()).details:
        console.warning(detail)


# determine changed services on host.
# param mode: can be one of "new", "remove", "fixall", "refresh", "only-host-labels"
# param servic_filter: if a filter is set, it controls whether items are touched by the discovery.
#                       if it returns False for a new item it will not be added, if it returns
#                       False for a vanished item, that item is kept
def automation_discovery(
    *,
    config_cache: config.ConfigCache,
    host_config: config.HostConfig,
    mode: DiscoveryMode,
    service_filters: Optional[_ServiceFilters],
    on_error: OnError,
    use_cached_snmp_data: bool,
    max_cachefile_age: cmk.core_helpers.cache.MaxAge,
) -> DiscoveryResult:

    console.verbose("  Doing discovery with mode '%s'...\n" % mode)

    host_name = host_config.hostname
    result = DiscoveryResult()

    if host_name not in config_cache.all_active_hosts():
        result.error_text = ""
        return result

    cmk.core_helpers.cache.FileCacheFactory.use_outdated = True
    cmk.core_helpers.cache.FileCacheFactory.maybe = use_cached_snmp_data

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

        if mode is not DiscoveryMode.REMOVE:
            host_labels = analyse_host_labels(
                host_config=host_config,
                ipaddress=ipaddress,
                parsed_sections_broker=parsed_sections_broker,
                load_labels=True,
                save_labels=True,
                on_error=on_error,
            )
            result.self_new_host_labels = len(host_labels.new)
            result.self_total_host_labels = len(host_labels.present)

        if mode is DiscoveryMode.ONLY_HOST_LABELS:
            # This is the result of a refactoring, and the following code was added
            # to ensure a compatible behaviour. I don't think it is particularly
            # sensible. We used to only compare service descriptions of old and new
            # services, so `make_object_diff` was always comparing two identical objects
            # if the mode was DiscoveryMode.ONLY_HOST_LABEL.
            # We brainlessly mimic that behaviour, for now.
            result.diff_text = make_object_diff(set(), set())
            return result

        # Compute current state of new and existing checks
        services = _get_host_services(
            host_config,
            ipaddress,
            parsed_sections_broker,
            on_error=on_error,
        )

        old_services = services.get("old", [])

        # Create new list of checks
        new_services = _get_post_discovery_services(host_name, services, service_filters or
                                                    _ServiceFilters.accept_all(), result, mode)
        host_config.set_autochecks(new_services)

        # If old_services == new_services, make_object_diff will return
        # something along the lines of "nothing changed".
        # I guess this was written before discovered host labels were invented.
        result.diff_text = make_object_diff(
            {x.service.description for x in old_services},
            {x.service.description for x in new_services},
        )

    except MKTimeout:
        raise  # let general timeout through

    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        result.error_text = str(e)

    result.self_total = result.self_new + result.self_kept
    return result


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
def active_check_discovery(
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    *,
    # The next argument *must* remain optional for the DiscoCheckExecutor.
    #   See Also: `cmk.base.agent_based.checking.active_check_checking()`.
    fetcher_messages: Sequence[FetcherMessage] = (),
) -> ActiveCheckResult:

    # Note: '--cache' is set in core_cmc, nagios template or even on CL and means:
    # 1. use caches as default:
    #    - Set FileCacheFactory.maybe = True (set max_cachefile_age, else 0)
    #    - Set FileCacheFactory.use_outdated = True
    # 2. Then these settings are used to read cache file or not

    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(host_name)

    params = host_config.discovery_check_parameters
    if params is None:
        params = host_config.default_discovery_check_parameters()
    rediscovery_parameters = params.get("inventory_rediscovery", {})

    discovery_mode = DiscoveryMode(rediscovery_parameters.get("mode"))

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
        file_cache_max_age=config.max_cachefile_age(
            discovery=None if cmk.core_helpers.cache.FileCacheFactory.maybe else 0),
        force_snmp_cache_refresh=False,
        on_scan_error=OnError.RAISE,
    )

    host_labels = analyse_host_labels(
        host_config=host_config,
        ipaddress=ipaddress,
        parsed_sections_broker=parsed_sections_broker,
        load_labels=True,
        save_labels=False,
        on_error=OnError.RAISE,
    )
    services = _get_host_services(
        host_config,
        ipaddress,
        parsed_sections_broker,
        on_error=OnError.RAISE,
    )

    services_result, services_need_rediscovery = _check_service_lists(
        host_name=host_name,
        services_by_transition=services,
        params=params,
        service_filters=_ServiceFilters.from_settings(rediscovery_parameters),
        discovery_mode=discovery_mode,
    )

    host_labels_result, host_labels_need_rediscovery = _check_host_labels(
        host_labels,
        int(params.get("severity_new_host_label", 1)),
        discovery_mode,
    )

    parsing_errors_result = check_parsing_errors(parsed_sections_broker.parsing_errors())

    return ActiveCheckResult.from_subresults(
        services_result,
        host_labels_result,
        *check_sources(source_results=source_results, mode=Mode.DISCOVERY),
        parsing_errors_result,
        _schedule_rediscovery(
            host_config=host_config,
            need_rediscovery=(services_need_rediscovery or host_labels_need_rediscovery) and
            parsing_errors_result.state == 0,
        ),
    )


def _check_service_lists(
    *,
    host_name: HostName,
    services_by_transition: ServicesByTransition,
    params: config.DiscoveryCheckParameters,
    service_filters: _ServiceFilters,
    discovery_mode: DiscoveryMode,
) -> Tuple[ActiveCheckResult, bool]:

    status = 0
    infotexts = []
    long_infotexts = []
    need_rediscovery = False

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

    return ActiveCheckResult(status, infotexts, long_infotexts, []), need_rediscovery


def _check_host_labels(
    host_labels: QualifiedDiscovery[HostLabel],
    severity_new_host_label: int,
    discovery_mode: DiscoveryMode,
) -> Tuple[ActiveCheckResult, bool]:
    return (
        ActiveCheckResult(severity_new_host_label, [f"{len(host_labels.new)} new host labels"], [],
                          []),
        discovery_mode in (DiscoveryMode.NEW, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH),
    ) if host_labels.new else (
        ActiveCheckResult(0, ["no new host labels"], [], []),
        False,
    )


def _schedule_rediscovery(
    *,
    host_config: config.HostConfig,
    need_rediscovery: bool,
) -> ActiveCheckResult:
    if not need_rediscovery:
        return ActiveCheckResult(0, (), (), ())

    autodiscovery_queue = _AutodiscoveryQueue()
    if host_config.is_cluster and host_config.nodes:
        for nodename in host_config.nodes:
            autodiscovery_queue.add(nodename)
    else:
        autodiscovery_queue.add(host_config.hostname)

    return ActiveCheckResult(0, ("rediscovery scheduled",), (), ())


class _AutodiscoveryQueue:
    @staticmethod
    def _host_name(file_path: Path) -> HostName:
        return HostName(file_path.stem)

    def _file_path(self, host_name: HostName) -> Path:
        return self._dir / str(host_name)

    def __init__(self):
        self._dir = Path(cmk.utils.paths.var_dir, 'autodiscovery')

    def _ls(self) -> Iterable[Path]:
        try:
            # we must consume the .iterdir generator to make sure
            # the FileNotFoundError gets rased *here*.
            return list(self._dir.iterdir())
        except FileNotFoundError:
            return []

    def oldest(self) -> Optional[float]:
        return min((f.stat().st_mtime for f in self._ls()), default=None)

    def queued_hosts(self) -> Iterable[HostName]:
        return (self._host_name(f) for f in self._ls())

    def add(self, host_name: HostName) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._file_path(host_name).touch()

    def remove(self, host_name: HostName) -> None:
        with suppress(FileNotFoundError):
            self._file_path(host_name).unlink()

    def cleanup(self, *, valid_hosts: Container[HostName], logger: Callable[[str], None]) -> None:
        for host_name in (hn for f in self._ls() if (hn := self._host_name(f)) not in valid_hosts):
            logger(f"  Removing mark '{host_name}' (host not configured)\n")
            self.remove(host_name)


def discover_marked_hosts(core: MonitoringCore) -> None:
    """Autodiscovery"""

    console.verbose("Doing discovery for all marked hosts:\n")
    autodiscovery_queue = _AutodiscoveryQueue()

    config_cache = config.get_config_cache()

    autodiscovery_queue.cleanup(
        valid_hosts=config_cache.all_configured_hosts(),
        logger=console.verbose,
    )

    oldest_queued = autodiscovery_queue.oldest()
    if oldest_queued is None:
        console.verbose("  Nothing to do. No hosts marked by discovery check.\n")
        return

    process_hosts = EVERYTHING if (up_hosts := _get_up_hosts()) is None else up_hosts

    activation_required = False
    rediscovery_reference_time = time.time()

    with TimeLimitFilter(limit=120, grace=10, label="hosts") as time_limited:
        for host_name in time_limited(autodiscovery_queue.queued_hosts()):
            if host_name not in process_hosts:
                continue

            activation_required |= _discover_marked_host(
                config_cache=config_cache,
                host_config=config_cache.get_host_config(host_name),
                autodiscovery_queue=autodiscovery_queue,
                reference_time=rediscovery_reference_time,
                oldest_queued=oldest_queued,
            )

    if not activation_required:
        return

    console.verbose("\nRestarting monitoring core with updated configuration...\n")
    with config.set_use_core_config(use_core_config=False):
        try:
            _config_cache.clear_all()
            config.get_config_cache().initialize()

            # reset these to their original value to create a correct config
            cmk.core_helpers.cache.FileCacheFactory.use_outdated = False
            cmk.core_helpers.cache.FileCacheFactory.maybe = True
            if config.monitoring_core == "cmc":
                cmk.base.core.do_reload(core)
            else:
                cmk.base.core.do_restart(core)
        finally:
            _config_cache.clear_all()
            config.get_config_cache().initialize()


def _get_up_hosts() -> Optional[Set[HostName]]:
    query = "GET hosts\nColumns: name state"
    try:
        response = livestatus.LocalConnection().query(query)
        return {HostName(name) for name, state in response if state == 0}
    except (livestatus.MKLivestatusNotFoundError, livestatus.MKLivestatusSocketError):
        pass
    return None


def _discover_marked_host(
    *,
    config_cache: config.ConfigCache,
    host_config: config.HostConfig,
    autodiscovery_queue: _AutodiscoveryQueue,
    reference_time: float,
    oldest_queued: float,
) -> bool:
    host_name = host_config.hostname
    console.verbose(f"{tty.bold}{host_name}{tty.normal}:\n")

    if host_config.discovery_check_parameters is None:
        console.verbose("  failed: discovery check disabled\n")
        return False
    rediscovery_parameters = host_config.discovery_check_parameters.get("inventory_rediscovery", {})

    reason = _may_rediscover(
        rediscovery_parameters=rediscovery_parameters,
        reference_time=reference_time,
        oldest_queued=oldest_queued,
    )
    if reason:
        console.verbose(f"  skipped: {reason}\n")
        return False

    result = automation_discovery(
        config_cache=config_cache,
        host_config=host_config,
        mode=DiscoveryMode(rediscovery_parameters.get("mode")),
        service_filters=_ServiceFilters.from_settings(rediscovery_parameters),
        on_error=OnError.IGNORE,
        use_cached_snmp_data=True,
        # autodiscovery is run every 5 minutes (see
        # omd/packages/check_mk/skel/etc/cron.d/cmk_discovery)
        # make sure we may use the file the active discovery check left behind:
        max_cachefile_age=config.max_cachefile_age(discovery=600),
    )
    if result.error_text is not None:
        # for offline hosts the error message is empty. This is to remain
        # compatible with the automation code
        console.verbose(f"  failed: {result.error_text or 'host is offline'}\n")
        # delete the file even in error case, otherwise we might be causing the same error
        # every time the cron job runs
        autodiscovery_queue.remove(host_name)
        return False

    something_changed = (result.self_new != 0 or result.self_removed != 0 or
                         result.self_kept != result.self_total or result.clustered_new != 0 or
                         result.clustered_vanished != 0 or result.self_new_host_labels != 0)

    if not something_changed:
        console.verbose("  nothing changed.\n")
        activation_required = False
    else:
        console.verbose(f"  {result.self_new} new, {result.self_removed} removed, "
                        f"{result.self_kept} kept, {result.self_total} total services "
                        f"and {result.self_new_host_labels} new host labels. "
                        f"clustered new {result.clustered_new}, clustered vanished "
                        f"{result.clustered_vanished}")

        # Note: Even if the actual mark-for-discovery flag may have been created by a cluster host,
        #       the activation decision is based on the discovery configuration of the node
        activation_required = bool(rediscovery_parameters["activation"])

        # Enforce base code creating a new host config object after this change
        config_cache.invalidate_host_config(host_name)

        # Now ensure that the discovery service is updated right after the changes
        schedule_discovery_check(host_name)

    autodiscovery_queue.remove(host_name)

    return activation_required


def _may_rediscover(
    rediscovery_parameters: Mapping,  # TODO
    reference_time: float,
    oldest_queued: float,
) -> str:
    if not set(rediscovery_parameters) >= {"excluded_time", "group_time"}:
        return "automatic discovery disabled for this host"

    now = time.gmtime(reference_time)
    for start_hours_mins, end_hours_mins in rediscovery_parameters["excluded_time"]:
        start_time = time.struct_time(
            (now.tm_year, now.tm_mon, now.tm_mday, start_hours_mins[0], start_hours_mins[1], 0,
             now.tm_wday, now.tm_yday, now.tm_isdst))

        end_time = time.struct_time((now.tm_year, now.tm_mon, now.tm_mday, end_hours_mins[0],
                                     end_hours_mins[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst))

        if start_time <= now <= end_time:
            return "we are currently in a disallowed time of day"

    # we could check this earlier. No need to to it for every host.
    if reference_time - oldest_queued < rediscovery_parameters["group_time"]:
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
    on_error: OnError,
) -> ServicesByTransition:

    services = _get_cluster_services(
        host_config,
        ipaddress,
        parsed_sections_broker,
        on_error,
    ) if host_config.is_cluster else _get_node_services(
        host_config.hostname,
        ipaddress,
        parsed_sections_broker,
        on_error,
        config.get_config_cache().host_of_clustered_service,
    )

    services.update(_manual_items(host_config))
    services.update(_custom_items(host_config))
    services.update(_active_items(host_config))
    services.update(_reclassify_disabled_items(host_config.hostname, services))

    return _group_by_transition(services)


# Do the actual work for a non-cluster host or node
def _get_node_services(
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    parsed_sections_broker: ParsedSectionsBroker,
    on_error: OnError,
    host_of_clustered_service: Callable[[HostName, str], str],
) -> ServicesTable:

    service_result = analyse_discovered_services(
        host_name=host_name,
        ipaddress=ipaddress,
        parsed_sections_broker=parsed_sections_broker,
        run_plugin_names=EVERYTHING,
        only_new=False,
        on_error=on_error,
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


def _manual_items(host_config: config.HostConfig) -> Iterable[Tuple[ServiceID, ServicesTableEntry]]:
    # Find manual checks. These can override discovered checks -> "manual"
    host_name = host_config.hostname
    yield from ((service.id(), ('manual', service, [
        host_name
    ])) for service in check_table.get_check_table(host_name, skip_autochecks=True).values())


def _custom_items(host_config: config.HostConfig) -> Iterable[Tuple[ServiceID, ServicesTableEntry]]:
    # Add custom checks -> "custom"
    yield from (((CheckPluginName('custom'), entry['service_description']), (
        'custom',
        Service(
            check_plugin_name=CheckPluginName('custom'),
            item=entry['service_description'],
            description=entry['service_description'],
            parameters=None,
        ),
        [host_config.hostname],
    )) for entry in host_config.custom_checks)


def _active_items(host_config: config.HostConfig) -> Iterable[Tuple[ServiceID, ServicesTableEntry]]:
    # Similar for 'active_checks', but here we have parameters
    host_name = host_config.hostname
    for plugin_name, entries in host_config.active_checks:
        for params in entries:
            descr = config.active_check_service_description(host_name, plugin_name, params)
            yield (CheckPluginName(plugin_name), descr), (
                'active',
                Service(
                    check_plugin_name=CheckPluginName(plugin_name),
                    item=descr,
                    description=descr,
                    parameters=params,
                ),
                [host_name],
            )


def _reclassify_disabled_items(
    host_name: HostName,
    services: ServicesTable,
) -> Iterable[Tuple[ServiceID, ServicesTableEntry]]:
    """Handle disabled services -> 'ignored'"""
    yield from (
        (discovered_service.id(), ("ignored", discovered_service, [host_name]))
        for check_source, discovered_service, _found_on_nodes in services.values()
        # These are ignored later in get_check_preview
        # TODO: This needs to be cleaned up. The problem here is that service_description() can not
        # calculate the description of active checks and the active checks need to be put into
        # "[source]_ignored" instead of ignored.
        if check_source not in {"legacy", "active", "custom"} and config.service_ignored(
            host_name, discovered_service.check_plugin_name, discovered_service.description))


def _group_by_transition(transition_services: ServicesTable) -> ServicesByTransition:
    services_by_transition: ServicesByTransition = {}
    for transition, service, found_on_nodes in transition_services.values():
        services_by_transition.setdefault(
            transition,
            [],
        ).append(autochecks.ServiceWithNodes(service, found_on_nodes))
    return services_by_transition


def _get_cluster_services(
    host_config: config.HostConfig,
    ipaddress: Optional[str],
    parsed_sections_broker: ParsedSectionsBroker,
    on_error: OnError,
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
            run_plugin_names=EVERYTHING,
            only_new=True,
            on_error=on_error,
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
    max_cachefile_age: cmk.core_helpers.cache.MaxAge,
    use_cached_snmp_data: bool,
    on_error: OnError,
) -> Tuple[CheckPreviewTable, QualifiedDiscovery[HostLabel]]:
    """Get the list of service of a host or cluster and guess the current state of
    all services if possible"""
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(host_name)

    ip_address = None if host_config.is_cluster else config.lookup_ip_address(host_config)

    cmk.core_helpers.cache.FileCacheFactory.use_outdated = True
    cmk.core_helpers.cache.FileCacheFactory.maybe = use_cached_snmp_data

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

    host_labels = analyse_host_labels(
        host_config=host_config,
        ipaddress=ip_address,
        parsed_sections_broker=parsed_sections_broker,
        load_labels=True,
        save_labels=False,
        on_error=on_error,
    )

    for detail in check_parsing_errors(parsed_sections_broker.parsing_errors()).details:
        console.warning(detail)

    grouped_services = _get_host_services(
        host_config,
        ip_address,
        parsed_sections_broker,
        on_error,
    )

    with load_host_value_store(host_name, store_changes=False) as value_store_manager:
        table = [
            _check_preview_table_row(
                host_config=host_config,
                ip_address=ip_address,
                service=service,
                check_source=check_source,
                parsed_sections_broker=parsed_sections_broker,
                found_on_nodes=found_on_nodes,
                value_store_manager=value_store_manager,
            )
            for check_source, services_with_nodes in grouped_services.items()
            for service, found_on_nodes in services_with_nodes
        ]

    return table, host_labels


def _check_preview_table_row(
    *,
    host_config: config.HostConfig,
    ip_address: Optional[HostAddress],
    service: Service,
    check_source: str,
    parsed_sections_broker: ParsedSectionsBroker,
    found_on_nodes: List[HostName],
    value_store_manager: ValueStoreManager,
) -> CheckPreviewEntry:
    plugin = agent_based_register.get_check_plugin(service.check_plugin_name)
    params = _preview_params(host_config.hostname, service, plugin, check_source)

    if check_source in ['legacy', 'active', 'custom']:
        exitcode = None
        output = u"WAITING - %s check, cannot be done offline" % check_source.title()
        ruleset_name: Optional[RulesetName] = None
    else:

        ruleset_name = (str(plugin.check_ruleset_name)
                        if plugin and plugin.check_ruleset_name else None)
        wrapped_params = (Parameters(wrap_parameters(params))
                          if plugin and plugin.check_default_parameters is not None else None)

        exitcode, output, _perfdata = checking.get_aggregated_result(
            parsed_sections_broker,
            host_config,
            ip_address,
            service,
            plugin,
            lambda p=wrapped_params: p,  # type: ignore[misc]  # "type of lambda"
            value_store_manager=value_store_manager,
        ).result

    # Service discovery never uses the perfdata in the check table. That entry
    # is constantly discarded, yet passed around(back and forth) as part of the
    # discovery result in the request elements. Some perfdata VALUES are not parsable
    # by ast.literal_eval such as "inf" it lead to ValueErrors. Thus keep perfdata empty
    perfdata: List[MetricTuple] = []

    return (
        _preview_check_source(host_config.hostname, service, check_source),
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
    )


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
