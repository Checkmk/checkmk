#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
import time
from contextlib import suppress
from pathlib import Path
from typing import (
    Callable,
    Container,
    Counter,
    Dict,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)

import livestatus

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.caching import config_cache as _config_cache
from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.exceptions import MKGeneralException, MKTimeout, OnError
from cmk.utils.log import console
from cmk.utils.parameters import TimespecificParameters
from cmk.utils.type_defs import (
    assert_never,
    CheckPluginName,
    DiscoveryResult,
    EVERYTHING,
    HostAddress,
    HostKey,
    HostName,
    RulesetName,
    ServiceName,
)

from cmk.automations.results import CheckPreviewEntry

import cmk.core_helpers.cache
from cmk.core_helpers.protocol import FetcherMessage
from cmk.core_helpers.type_defs import Mode, NO_SELECTION, SectionNameCollection

import cmk.base.agent_based.checking as checking
import cmk.base.agent_based.decorator as decorator
import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.autochecks as autochecks
import cmk.base.check_table as check_table
import cmk.base.check_utils
import cmk.base.config as config
import cmk.base.core
import cmk.base.crash_reporting
import cmk.base.section as section
from cmk.base.agent_based.data_provider import make_broker, ParsedSectionsBroker
from cmk.base.agent_based.utils import check_parsing_errors, check_sources
from cmk.base.api.agent_based.value_store import load_host_value_store, ValueStoreManager
from cmk.base.check_utils import ConfiguredService, LegacyCheckParameters, ServiceID
from cmk.base.core_config import (
    get_active_check_descriptions,
    get_host_attributes,
    MonitoringCore,
    ObjectAttributes,
)
from cmk.base.discovered_labels import HostLabel, ServiceLabel
from cmk.base.sources import fetch_all, make_sources, Source

from ._discovered_services import analyse_discovered_services
from ._filters import ServiceFilters as _ServiceFilters
from ._host_labels import analyse_host_labels, analyse_node_labels
from .utils import DiscoveryMode, QualifiedDiscovery, TimeLimitFilter

_BasicTransition = Literal["old", "new", "vanished"]
_Transition = Union[
    _BasicTransition,
    Literal["ignored", "clustered_old", "clustered_new", "clustered_vanished", "clustered_ignored"],
]


_L = TypeVar("_L", bound=str)

ServicesTableEntry = Tuple[_L, autochecks.AutocheckEntry, List[HostName]]
ServicesTable = Dict[ServiceID, ServicesTableEntry[_L]]
ServicesByTransition = Dict[_Transition, List[autochecks.AutocheckServiceWithNodes]]


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
    service = (
        "Check_MK Discovery"
        if "cmk_inventory" in config.use_new_descriptions_for
        else "Check_MK inventory"
    )
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


# .
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
            fetched = fetch_all(
                sources=make_sources(
                    config_cache,
                    host_config,
                    config.lookup_ip_address(host_config),
                    selected_sections=selected_sections,
                    force_snmp_cache_refresh=False,
                    on_scan_error=on_error,
                ),
                file_cache_max_age=config.max_cachefile_age(),
                mode=mode,
            )
            parsed_sections_broker, _results = make_broker(
                fetched=fetched,
                selected_sections=selected_sections,
                file_cache_max_age=config.max_cachefile_age(),
            )
            _commandline_discovery_on_host(
                host_key=host_config.host_key,
                host_key_mgmt=host_config.host_key_mgmt,
                parsed_sections_broker=parsed_sections_broker,
                run_plugin_names=run_plugin_names,
                only_new=arg_only_new,
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
        console.verbose(
            "Discovering %shost labels on all hosts\n"
            % ("services and " if not only_host_labels else "")
        )
        arg_host_names = config_cache.all_active_realhosts()
    else:
        console.verbose(
            "Discovering %shost labels on: %s\n"
            % ("services and " if not only_host_labels else "", ", ".join(sorted(arg_host_names)))
        )

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
    *,
    host_key: HostKey,
    host_key_mgmt: HostKey,
    parsed_sections_broker: ParsedSectionsBroker,
    run_plugin_names: Container[CheckPluginName],
    only_new: bool,
    load_labels: bool,
    only_host_labels: bool,
    on_error: OnError,
) -> None:

    section.section_step("Analyse discovered host labels")

    host_labels = analyse_node_labels(
        host_key=host_key,
        host_key_mgmt=host_key_mgmt,
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
        host_key=host_key,
        host_key_mgmt=host_key_mgmt,
        parsed_sections_broker=parsed_sections_broker,
        run_plugin_names=run_plugin_names,
        forget_existing=not only_new,
        keep_vanished=only_new,
        on_error=on_error,
    )

    # TODO (mo): for the labels the corresponding code is in _host_labels.
    # We should put the persisting in one place.
    autochecks.AutochecksStore(host_key.hostname).write(service_result.present)

    new_per_plugin = Counter(s.check_plugin_name for s in service_result.new)
    for name, count in sorted(new_per_plugin.items()):
        console.verbose("%s%3d%s %s\n" % (tty.green + tty.bold, count, tty.normal, name))

    count = len(service_result.new) if service_result.new else ("no new" if only_new else "no")
    section.section_success(f"Found {count} services")

    for result in check_parsing_errors(parsed_sections_broker.parsing_errors()):
        for line in result.details:
            console.warning(line)


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

        ipaddress = None if host_config.is_cluster else config.lookup_ip_address(host_config)

        fetched = fetch_all(
            sources=make_sources(
                config_cache,
                host_config,
                ipaddress,
                selected_sections=NO_SELECTION,
                force_snmp_cache_refresh=not use_cached_snmp_data,
                on_scan_error=on_error,
            ),
            file_cache_max_age=max_cachefile_age,
            mode=Mode.DISCOVERY,
        )
        parsed_sections_broker, _source_results = make_broker(
            fetched=fetched,
            selected_sections=NO_SELECTION,
            file_cache_max_age=max_cachefile_age,
        )

        if mode is not DiscoveryMode.REMOVE:
            host_labels = analyse_host_labels(
                host_config=host_config,
                parsed_sections_broker=parsed_sections_broker,
                load_labels=True,
                save_labels=True,
                on_error=on_error,
            )
            result.self_new_host_labels = len(host_labels.new)
            result.self_total_host_labels = len(host_labels.present)

            if mode is DiscoveryMode.ONLY_HOST_LABELS:
                result.diff_text = _make_diff(host_labels.vanished, host_labels.new, (), ())
                return result
        else:
            host_labels = QualifiedDiscovery.empty()

        # Compute current state of new and existing checks
        services = _get_host_services(
            host_config,
            parsed_sections_broker,
            on_error=on_error,
        )

        old_services = {x.service.id(): x for x in services.get("old", [])}

        # Create new list of checks
        final_services = _get_post_discovery_autocheck_services(
            host_name, services, service_filters or _ServiceFilters.accept_all(), result, mode
        )
        host_config.set_autochecks(list(final_services.values()))

        result.diff_text = _make_diff(
            host_labels.vanished,
            host_labels.new,
            (x.service for x in old_services.values() if x.service.id() not in final_services),
            (x.service for x in final_services.values() if x.service.id() not in old_services),
        )

    except MKTimeout:
        raise  # let general timeout through

    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        result.error_text = str(e)

    result.self_total = result.self_new + result.self_kept
    return result


def _get_post_discovery_autocheck_services(  # pylint: disable=too-many-branches
    host_name: HostName,
    services: ServicesByTransition,
    service_filters: _ServiceFilters,
    result: DiscoveryResult,
    mode: DiscoveryMode,
) -> Mapping[ServiceID, autochecks.AutocheckServiceWithNodes]:
    """
    The output contains a selction of services in the states "new", "old", "ignored", "vanished"
    (depending on the value of `mode`) and "clusterd_".

    Service in with the state "custom", "active" and "manual" are currently not checked.

    Note:

        Discovered services that are shadowed by enforces services will vanish that way.

    """
    post_discovery_services = {}
    for check_source, discovered_services_with_nodes in services.items():

        if check_source == "new":
            if mode in (DiscoveryMode.NEW, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH):
                new = {
                    s.service.id(): s
                    for s in discovered_services_with_nodes
                    if service_filters.new(config.service_description(host_name, *s.service.id()))
                }
                result.self_new += len(new)
                post_discovery_services.update(new)

        elif (
            check_source == "old" or check_source == "ignored"  # pylint: disable=consider-using-in
        ):
            # keep currently existing valid services in any case
            post_discovery_services.update(
                (s.service.id(), s) for s in discovered_services_with_nodes
            )
            result.self_kept += len(discovered_services_with_nodes)

        elif check_source == "vanished":
            # keep item, if we are currently only looking for new services
            # otherwise fix it: remove ignored and non-longer existing services
            for entry in discovered_services_with_nodes:
                if mode in (
                    DiscoveryMode.FIXALL,
                    DiscoveryMode.REMOVE,
                ) and service_filters.vanished(
                    config.service_description(host_name, *entry.service.id())
                ):
                    result.self_removed += 1
                else:
                    post_discovery_services[entry.service.id()] = entry
                    result.self_kept += 1

        else:
            # Silently keep clustered services
            post_discovery_services.update(
                (s.service.id(), s) for s in discovered_services_with_nodes
            )
            if check_source == "clustered_new":
                result.clustered_new += len(discovered_services_with_nodes)
            elif check_source == "clustered_old":
                result.clustered_old += len(discovered_services_with_nodes)
            elif check_source == "clustered_vanished":
                result.clustered_vanished += len(discovered_services_with_nodes)
            elif check_source == "clustered_ignored":
                result.clustered_ignored += len(discovered_services_with_nodes)
            else:
                assert_never(check_source)

    return post_discovery_services


def _make_diff(
    labels_vanished: Iterable[HostLabel],
    labels_new: Iterable[HostLabel],
    services_vanished: Iterable[autochecks.AutocheckEntry],
    services_new: Iterable[autochecks.AutocheckEntry],
) -> str:
    """Textual representation of what changed

    This is very similar to `cmk.utils.object_diff.make_object_diff`, but the rendering is easier to
    read (since we have objects of different type), and we already know the new/removed items.
    """
    return (
        "\n".join(
            [
                *(f"Removed host label: '{l.label}'." for l in labels_vanished),
                *(f"Added host label: '{l.label}'." for l in labels_new),
                *(
                    (
                        f"Removed service: Check plugin '{s.check_plugin_name}'."
                        if s.item is None
                        else f"Removed service: Check plugin '{s.check_plugin_name}' / item '{s.item}'."
                    )
                    for s in services_vanished
                ),
                *(
                    (
                        f"Added service: Check plugin '{s.check_plugin_name}'."
                        if s.item is None
                        else f"Added service: Check plugin '{s.check_plugin_name}' / item '{s.item}'."
                    )
                    for s in services_new
                ),
            ]
        )
        or "Nothing was changed."
    )


# .
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
    *,
    fetched: Sequence[Tuple[Source, FetcherMessage]],
) -> ActiveCheckResult:
    return _execute_check_discovery(host_name, fetched=fetched)


@decorator.handle_check_mk_check_result("discovery", "Check_MK Discovery")
def commandline_check_discovery(
    host_name: HostName,
    ipaddress: Optional[HostAddress],
) -> ActiveCheckResult:
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(host_name)

    # In case of keepalive discovery we always have an ipaddress. When called as non keepalive
    # ipaddress is always None
    if ipaddress is None and not host_config.is_cluster:
        ipaddress = config.lookup_ip_address(host_config)

    fetched = fetch_all(
        sources=make_sources(
            config_cache,
            host_config,
            ipaddress,
            selected_sections=NO_SELECTION,
            force_snmp_cache_refresh=False,
            on_scan_error=OnError.RAISE,
        ),
        file_cache_max_age=config.max_cachefile_age(
            discovery=None if cmk.core_helpers.cache.FileCacheFactory.maybe else 0
        ),
        mode=Mode.DISCOVERY,
    )

    return _execute_check_discovery(host_name, fetched=fetched)


def _execute_check_discovery(
    host_name: HostName,
    *,
    fetched: Sequence[Tuple[Source, FetcherMessage]],
) -> ActiveCheckResult:
    # Note: '--cache' is set in core_cmc, nagios template or even on CL and means:
    # 1. use caches as default:
    #    - Set FileCacheFactory.maybe = True (set max_cachefile_age, else 0)
    #    - Set FileCacheFactory.use_outdated = True
    # 2. Then these settings are used to read cache file or not

    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(host_name)
    params = host_config.discovery_check_parameters()

    discovery_mode = DiscoveryMode(params.rediscovery.get("mode"))

    parsed_sections_broker, source_results = make_broker(
        fetched=fetched,
        selected_sections=NO_SELECTION,
        file_cache_max_age=config.max_cachefile_age(
            discovery=None if cmk.core_helpers.cache.FileCacheFactory.maybe else 0
        ),
    )

    host_labels = analyse_host_labels(
        host_config=host_config,
        parsed_sections_broker=parsed_sections_broker,
        load_labels=True,
        save_labels=False,
        on_error=OnError.RAISE,
    )
    services = _get_host_services(
        host_config,
        parsed_sections_broker,
        on_error=OnError.RAISE,
    )

    services_result, services_need_rediscovery = _check_service_lists(
        host_name=host_name,
        services_by_transition=services,
        params=params,
        service_filters=_ServiceFilters.from_settings(params.rediscovery),
        discovery_mode=discovery_mode,
    )

    host_labels_result, host_labels_need_rediscovery = _check_host_labels(
        host_labels,
        params.severity_new_host_labels,
        discovery_mode,
    )

    parsing_errors_results = check_parsing_errors(parsed_sections_broker.parsing_errors())

    return ActiveCheckResult.from_subresults(
        *services_result,
        host_labels_result,
        *check_sources(source_results=source_results),
        *parsing_errors_results,
        _schedule_rediscovery(
            host_config=host_config,
            need_rediscovery=(services_need_rediscovery or host_labels_need_rediscovery)
            and all(r.state == 0 for r in parsing_errors_results),
        ),
    )


def _check_service_lists(
    *,
    host_name: HostName,
    services_by_transition: ServicesByTransition,
    params: config.DiscoveryCheckParameters,
    service_filters: _ServiceFilters,
    discovery_mode: DiscoveryMode,
) -> Tuple[Sequence[ActiveCheckResult], bool]:

    subresults = []
    need_rediscovery = False

    for transition, t_services, title, severity, service_filter in [
        (
            "new",
            services_by_transition.get("new", []),
            "unmonitored",
            params.severity_new_services,
            service_filters.new,
        ),
        (
            "vanished",
            services_by_transition.get("vanished", []),
            "vanished",
            params.severity_vanished_services,
            service_filters.vanished,
        ),
    ]:

        affected_check_plugin_names: Counter[CheckPluginName] = Counter()
        unfiltered = False

        for (discovered_service, _found_on_nodes) in t_services:
            affected_check_plugin_names[discovered_service.check_plugin_name] += 1

            if not unfiltered and service_filter(
                config.service_description(host_name, *discovered_service.id())
            ):
                unfiltered = True

            subresults.append(
                ActiveCheckResult(
                    0,
                    "",
                    [
                        "%s: %s: %s"
                        % (
                            title.capitalize(),
                            discovered_service.check_plugin_name,
                            config.service_description(host_name, *discovered_service.id()),
                        )
                    ],
                )
            )

        if affected_check_plugin_names:
            info = ", ".join(["%s: %d" % e for e in affected_check_plugin_names.items()])
            count = sum(affected_check_plugin_names.values())
            subresults.append(
                ActiveCheckResult(severity, f"{title.capitalize()} services: {count} ({info})")
            )

            if unfiltered and (
                (
                    transition == "new"
                    and discovery_mode
                    in (DiscoveryMode.NEW, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH)
                )
                or (
                    transition == "vanished"
                    and discovery_mode
                    in (DiscoveryMode.REMOVE, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH)
                )
            ):
                need_rediscovery = True
        else:
            subresults.append(ActiveCheckResult(0, "", [f"No {title} services found"]))

    for (discovered_service, _found_on_nodes) in services_by_transition.get("ignored", []):
        subresults.append(
            ActiveCheckResult(
                0,
                "",
                [
                    "Ignored: %s: %s"
                    % (
                        discovered_service.check_plugin_name,
                        config.service_description(host_name, *discovered_service.id()),
                    )
                ],
            )
        )

    if not any(s.summary for s in subresults):
        subresults.insert(0, ActiveCheckResult(0, "All services up to date"))
    return subresults, need_rediscovery


def _check_host_labels(
    host_labels: QualifiedDiscovery[HostLabel],
    severity_new_host_label: int,
    discovery_mode: DiscoveryMode,
) -> Tuple[ActiveCheckResult, bool]:
    return (
        (
            ActiveCheckResult(severity_new_host_label, f"New host labels: {len(host_labels.new)}"),
            discovery_mode in (DiscoveryMode.NEW, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH),
        )
        if host_labels.new
        else (
            ActiveCheckResult(0, "All host labels up to date"),
            False,
        )
    )


def _schedule_rediscovery(
    *,
    host_config: config.HostConfig,
    need_rediscovery: bool,
) -> ActiveCheckResult:
    if not need_rediscovery:
        return ActiveCheckResult()

    autodiscovery_queue = _AutodiscoveryQueue()
    if host_config.is_cluster and host_config.nodes:
        for nodename in host_config.nodes:
            autodiscovery_queue.add(nodename)
    else:
        autodiscovery_queue.add(host_config.hostname)

    return ActiveCheckResult(0, "rediscovery scheduled")


class _AutodiscoveryQueue:
    @staticmethod
    def _host_name(file_path: Path) -> HostName:
        return HostName(file_path.name)

    def _file_path(self, host_name: HostName) -> Path:
        return self._dir / str(host_name)

    def __init__(self) -> None:
        self._dir = Path(cmk.utils.paths.var_dir, "autodiscovery")

    def _ls(self) -> Iterable[Path]:
        try:
            # we must consume the .iterdir generator to make sure
            # the FileNotFoundError gets raised *here*.
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

    if (params := host_config.discovery_check_parameters()).commandline_only:
        console.verbose("  failed: discovery check disabled\n")
        return False

    reason = _may_rediscover(
        rediscovery_parameters=params.rediscovery,
        reference_time=reference_time,
        oldest_queued=oldest_queued,
    )
    if reason:
        console.verbose(f"  skipped: {reason}\n")
        return False

    result = automation_discovery(
        config_cache=config_cache,
        host_config=host_config,
        mode=DiscoveryMode(params.rediscovery.get("mode")),
        service_filters=_ServiceFilters.from_settings(params.rediscovery),
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

    something_changed = (
        result.self_new != 0
        or result.self_removed != 0
        or result.self_kept != result.self_total
        or result.clustered_new != 0
        or result.clustered_vanished != 0
        or result.self_new_host_labels != 0
    )

    if not something_changed:
        console.verbose("  nothing changed.\n")
        activation_required = False
    else:
        console.verbose(
            f"  {result.self_new} new, {result.self_removed} removed, "
            f"{result.self_kept} kept, {result.self_total} total services "
            f"and {result.self_new_host_labels} new host labels. "
            f"clustered new {result.clustered_new}, clustered vanished "
            f"{result.clustered_vanished}"
        )

        # Note: Even if the actual mark-for-discovery flag may have been created by a cluster host,
        #       the activation decision is based on the discovery configuration of the node
        activation_required = bool(params.rediscovery["activation"])

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
            (
                now.tm_year,
                now.tm_mon,
                now.tm_mday,
                start_hours_mins[0],
                start_hours_mins[1],
                0,
                now.tm_wday,
                now.tm_yday,
                now.tm_isdst,
            )
        )

        end_time = time.struct_time(
            (
                now.tm_year,
                now.tm_mon,
                now.tm_mday,
                end_hours_mins[0],
                end_hours_mins[1],
                0,
                now.tm_wday,
                now.tm_yday,
                now.tm_isdst,
            )
        )

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
#    "ignored"       : discovered or static, but disabled via ignored_services
#    "clustered_new" : New service found on a node that belongs to a cluster
#    "clustered_old" : Old service found on a node that belongs to a cluster
# This function is cluster-aware
def _get_host_services(
    host_config: config.HostConfig,
    parsed_sections_broker: ParsedSectionsBroker,
    on_error: OnError,
) -> ServicesByTransition:

    services: ServicesTable[_Transition]
    if host_config.is_cluster:
        services = {
            **_get_cluster_services(
                host_config,
                parsed_sections_broker,
                on_error,
            )
        }
    else:
        services = {
            **_get_node_services(
                host_key=host_config.host_key,
                host_key_mgmt=host_config.host_key_mgmt,
                parsed_sections_broker=parsed_sections_broker,
                on_error=on_error,
                host_of_clustered_service=config.get_config_cache().host_of_clustered_service,
            )
        }

    services.update(_reclassify_disabled_items(host_config.hostname, services))

    # remove the ones shadowed by enforced services
    enforced_services = _enforced_services(host_config)
    return _group_by_transition({k: v for k, v in services.items() if k not in enforced_services})


# Do the actual work for a non-cluster host or node
def _get_node_services(
    host_key: HostKey,
    host_key_mgmt: HostKey,
    parsed_sections_broker: ParsedSectionsBroker,
    on_error: OnError,
    host_of_clustered_service: Callable[[HostName, ServiceName], HostName],
) -> ServicesTable[_Transition]:

    service_result = analyse_discovered_services(
        host_key=host_key,
        host_key_mgmt=host_key_mgmt,
        parsed_sections_broker=parsed_sections_broker,
        run_plugin_names=EVERYTHING,
        forget_existing=False,
        keep_vanished=False,
        on_error=on_error,
    )

    return {
        entry.id(): (
            _node_service_source(
                check_source=check_source,
                host_name=host_key.hostname,
                cluster_name=host_of_clustered_service(host_key.hostname, service_name),
                check_plugin_name=entry.check_plugin_name,
                service_name=service_name,
            ),
            entry,
            [host_key.hostname],
        )
        for check_source, entry in service_result.chain_with_qualifier()
        if (service_name := config.service_description(host_key.hostname, *entry.id()))
    }


def _node_service_source(
    *,
    check_source: _BasicTransition,
    host_name: HostName,
    cluster_name: HostName,
    check_plugin_name: CheckPluginName,
    service_name: ServiceName,
) -> _Transition:
    if host_name == cluster_name:
        return check_source

    if config.service_ignored(cluster_name, check_plugin_name, service_name):
        return "ignored"

    if check_source == "vanished":
        return "clustered_vanished"
    if check_source == "old":
        return "clustered_old"
    return "clustered_new"


def _enforced_services(
    host_config: config.HostConfig,
) -> Mapping[ServiceID, ConfiguredService]:
    return check_table.get_check_table(host_config.hostname, skip_autochecks=True)


def _reclassify_disabled_items(
    host_name: HostName,
    services: ServicesTable[_Transition],
) -> Iterable[Tuple[ServiceID, ServicesTableEntry]]:
    """Handle disabled services -> 'ignored'"""
    yield from (
        (service.id(), ("ignored", service, [host_name]))
        for check_source, service, _found_on_nodes in services.values()
        if config.service_ignored(
            host_name,
            service.check_plugin_name,
            config.service_description(host_name, *service.id()),
        )
    )


def _group_by_transition(
    transition_services: ServicesTable[_Transition],
) -> ServicesByTransition:
    services_by_transition: ServicesByTransition = {}
    for transition, service, found_on_nodes in transition_services.values():
        services_by_transition.setdefault(
            transition,
            [],
        ).append(autochecks.AutocheckServiceWithNodes(service, found_on_nodes))
    return services_by_transition


def _get_cluster_services(
    host_config: config.HostConfig,
    parsed_sections_broker: ParsedSectionsBroker,
    on_error: OnError,
) -> ServicesTable[_Transition]:

    if not host_config.nodes:
        return {}

    cluster_items: ServicesTable[_BasicTransition] = {}
    config_cache = config.get_config_cache()

    # Get services of the nodes. We are only interested in "old", "new" and "vanished"
    # From the states and parameters of these we construct the final state per service.
    for node in host_config.nodes:
        node_config = config_cache.get_host_config(node)

        entries = analyse_discovered_services(
            host_key=node_config.host_key,
            host_key_mgmt=node_config.host_key_mgmt,
            parsed_sections_broker=parsed_sections_broker,
            run_plugin_names=EVERYTHING,
            forget_existing=False,
            keep_vanished=False,
            on_error=on_error,
        )

        for check_source, entry in entries.chain_with_qualifier():
            cluster_items.update(
                _cluster_service_entry(
                    check_source=check_source,
                    host_name=host_config.hostname,
                    node_name=node,
                    services_cluster=config_cache.host_of_clustered_service(
                        node, config.service_description(node, *entry.id())
                    ),
                    entry=entry,
                    existing_entry=cluster_items.get(entry.id()),
                )
            )

    return {**cluster_items}  # for the typing...


def _cluster_service_entry(
    *,
    check_source: _BasicTransition,
    host_name: HostName,
    node_name: HostName,
    services_cluster: HostName,
    entry: autochecks.AutocheckEntry,
    existing_entry: Optional[ServicesTableEntry[_BasicTransition]],
) -> Iterable[Tuple[ServiceID, ServicesTableEntry[_BasicTransition]]]:
    if host_name != services_cluster:
        return  # not part of this host

    if existing_entry is None:
        yield entry.id(), (check_source, entry, [node_name])
        return

    first_check_source, existing_ac_entry, nodes_with_service = existing_entry
    if node_name not in nodes_with_service:
        nodes_with_service.append(node_name)

    if first_check_source == "old":
        return

    if check_source == "old":
        yield entry.id(), (check_source, entry, nodes_with_service)
        return

    if {first_check_source, check_source} == {"vanished", "new"}:
        yield existing_ac_entry.id(), ("old", existing_ac_entry, nodes_with_service)
        return

    # In all other cases either both must be "new" or "vanished" -> let it be


def get_check_preview(
    *,
    host_name: HostName,
    max_cachefile_age: cmk.core_helpers.cache.MaxAge,
    use_cached_snmp_data: bool,
    on_error: OnError,
) -> Tuple[Sequence[CheckPreviewEntry], QualifiedDiscovery[HostLabel]]:
    """Get the list of service of a host or cluster and guess the current state of
    all services if possible"""
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(host_name)

    ip_address = None if host_config.is_cluster else config.lookup_ip_address(host_config)
    host_attrs = get_host_attributes(host_name, config_cache)

    cmk.core_helpers.cache.FileCacheFactory.use_outdated = True
    cmk.core_helpers.cache.FileCacheFactory.maybe = use_cached_snmp_data

    fetched = fetch_all(
        sources=make_sources(
            config_cache,
            host_config,
            ip_address,
            selected_sections=NO_SELECTION,
            force_snmp_cache_refresh=not use_cached_snmp_data,
            on_scan_error=on_error,
        ),
        file_cache_max_age=max_cachefile_age,
        mode=Mode.DISCOVERY,
    )
    parsed_sections_broker, _source_results = make_broker(
        fetched=fetched,
        selected_sections=NO_SELECTION,
        file_cache_max_age=max_cachefile_age,
    )

    host_labels = analyse_host_labels(
        host_config=host_config,
        parsed_sections_broker=parsed_sections_broker,
        load_labels=True,
        save_labels=False,
        on_error=on_error,
    )

    for result in check_parsing_errors(parsed_sections_broker.parsing_errors()):
        for line in result.details:
            console.warning(line)

    grouped_services = _get_host_services(
        host_config,
        parsed_sections_broker,
        on_error,
    )

    with load_host_value_store(host_name, store_changes=False) as value_store_manager:
        passive_rows = [
            _check_preview_table_row(
                host_config=host_config,
                service=ConfiguredService(
                    check_plugin_name=entry.check_plugin_name,
                    item=entry.item,
                    description=config.service_description(host_name, *entry.id()),
                    parameters=config.compute_check_parameters(
                        host_config.hostname,
                        entry.check_plugin_name,
                        entry.item,
                        entry.parameters,
                    ),
                    discovered_parameters=entry.parameters,
                    service_labels={n: ServiceLabel(n, v) for n, v in entry.service_labels.items()},
                ),
                check_source=check_source,
                parsed_sections_broker=parsed_sections_broker,
                found_on_nodes=found_on_nodes,
                value_store_manager=value_store_manager,
            )
            for check_source, services_with_nodes in grouped_services.items()
            for entry, found_on_nodes in services_with_nodes
        ] + [
            _check_preview_table_row(
                host_config=host_config,
                service=service,
                check_source="manual",  # "enforced" would be nicer
                parsed_sections_broker=parsed_sections_broker,
                found_on_nodes=[host_config.hostname],
                value_store_manager=value_store_manager,
            )
            for service in _enforced_services(host_config).values()
        ]

    return [
        *passive_rows,
        *_active_check_preview_rows(host_config, host_attrs),
        *_custom_check_preview_rows(host_config),
    ], host_labels


def _check_preview_table_row(
    *,
    host_config: config.HostConfig,
    service: ConfiguredService,
    check_source: Union[_Transition, Literal["manual"]],
    parsed_sections_broker: ParsedSectionsBroker,
    found_on_nodes: Sequence[HostName],
    value_store_manager: ValueStoreManager,
) -> CheckPreviewEntry:
    plugin = agent_based_register.get_check_plugin(service.check_plugin_name)
    ruleset_name = str(plugin.check_ruleset_name) if plugin and plugin.check_ruleset_name else None

    result = checking.get_aggregated_result(
        parsed_sections_broker,
        host_config,
        service,
        plugin,
        value_store_manager=value_store_manager,
    ).result

    return _make_check_preview_entry(
        host_name=host_config.hostname,
        check_plugin_name=str(service.check_plugin_name),
        item=service.item,
        description=service.description,
        check_source=check_source,
        ruleset_name=ruleset_name,
        discovered_parameters=service.discovered_parameters,
        effective_parameters=service.parameters,
        exitcode=result.state,
        output=result.output,
        found_on_nodes=found_on_nodes,
        labels={l.name: l.value for l in service.service_labels.values()},
    )


def _custom_check_preview_rows(
    host_config: config.HostConfig,
) -> Sequence[CheckPreviewEntry]:
    return list(
        {
            entry["service_description"]: _make_check_preview_entry(
                host_name=host_config.hostname,
                check_plugin_name="custom",
                item=entry["service_description"],
                description=entry["service_description"],
                check_source="ignored_custom"
                if config.service_ignored(
                    host_config.hostname, None, description=entry["service_description"]
                )
                else "custom",
            )
            for entry in host_config.custom_checks
        }.values()
    )


def _active_check_preview_rows(
    host_config: config.HostConfig,
    host_attrs: ObjectAttributes,
) -> Sequence[CheckPreviewEntry]:
    return list(
        {
            descr: _make_check_preview_entry(
                host_name=host_config.hostname,
                check_plugin_name=plugin_name,
                item=descr,
                description=descr,
                check_source="ignored_active"
                if config.service_ignored(host_config.hostname, None, descr)
                else "active",
                effective_parameters=params,
            )
            for plugin_name, entries in host_config.active_checks
            for params in entries
            for descr in get_active_check_descriptions(
                host_config.hostname, host_config.alias, host_attrs, plugin_name, params
            )
        }.values()
    )


def _make_check_preview_entry(
    *,
    host_name: HostName,
    check_plugin_name: str,
    item: Optional[str],
    description: ServiceName,
    check_source: str,
    ruleset_name: Optional[RulesetName] = None,
    discovered_parameters: LegacyCheckParameters = None,
    effective_parameters: Union[LegacyCheckParameters, TimespecificParameters] = None,
    exitcode: Optional[int] = None,
    output: str = "",
    found_on_nodes: Optional[Sequence[HostName]] = None,
    labels: Optional[Dict[str, str]] = None,
) -> CheckPreviewEntry:
    return CheckPreviewEntry(
        check_source=check_source,
        check_plugin_name=check_plugin_name,
        ruleset_name=ruleset_name,
        item=item,
        discovered_parameters=discovered_parameters,
        effective_parameters=_wrap_timespecific_for_preview(effective_parameters),
        description=description,
        state=exitcode,
        output=output
        or f"WAITING - {check_source.split('_')[-1].title()} check, cannot be done offline",
        # Service discovery never uses the perfdata in the check table. That entry
        # is constantly discarded, yet passed around(back and forth) as part of the
        # discovery result in the request elements. Some perfdata VALUES are not parsable
        # by ast.literal_eval such as "inf" it lead to ValueErrors. Thus keep perfdata empty
        metrics=[],
        labels=labels or {},
        found_on_nodes=[host_name] if found_on_nodes is None else list(found_on_nodes),
    )


def _wrap_timespecific_for_preview(
    params: Union[LegacyCheckParameters, TimespecificParameters]
) -> LegacyCheckParameters:
    return (
        params.preview(cmk.base.core.timeperiod_active)
        if isinstance(params, TimespecificParameters)
        else params
    )
