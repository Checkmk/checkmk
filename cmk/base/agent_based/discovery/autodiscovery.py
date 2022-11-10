#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
import socket
import time
from pathlib import Path
from typing import (
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

from typing_extensions import assert_never

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.caching import config_cache as _config_cache
from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.exceptions import MKTimeout, OnError
from cmk.utils.log import console
from cmk.utils.type_defs import (
    AgentRawData,
    CheckPluginName,
    DiscoveryResult,
    EVERYTHING,
    HostName,
    ServiceID,
    ServiceName,
)
from cmk.utils.type_defs.result import Result

from cmk.snmplib.type_defs import SNMPRawData

import cmk.core_helpers.cache
from cmk.core_helpers.type_defs import Mode, NO_SELECTION, SourceInfo

import cmk.base.autochecks as autochecks
import cmk.base.check_utils
import cmk.base.config as config
import cmk.base.core
import cmk.base.crash_reporting
from cmk.base.agent_based.data_provider import (
    make_broker,
    parse_messages,
    ParsedSectionsBroker,
    store_piggybacked_sections,
)
from cmk.base.auto_queue import AutoQueue, get_up_hosts, TimeLimitFilter
from cmk.base.config import ConfigCache, HostConfig
from cmk.base.core_config import MonitoringCore
from cmk.base.discovered_labels import HostLabel
from cmk.base.sources import fetch_all, make_sources

from ._discovered_services import analyse_discovered_services
from ._filters import ServiceFilters as _ServiceFilters
from ._host_labels import analyse_host_labels
from .utils import DiscoveryMode, QualifiedDiscovery

__all__ = ["schedule_discovery_check", "get_host_services"]

_BasicTransition = Literal["old", "new", "vanished"]
_Transition = Union[
    _BasicTransition,
    Literal["ignored", "clustered_old", "clustered_new", "clustered_vanished", "clustered_ignored"],
]


_L = TypeVar("_L", bound=str)

ServicesTableEntry = Tuple[_L, autochecks.AutocheckEntry, List[HostName]]
ServicesTable = Dict[ServiceID, ServicesTableEntry[_L]]
ServicesByTransition = Dict[_Transition, List[autochecks.AutocheckServiceWithNodes]]


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


# determine changed services on host.
# param mode: can be one of "new", "remove", "fixall", "refresh", "only-host-labels"
# param servic_filter: if a filter is set, it controls whether items are touched by the discovery.
#                       if it returns False for a new item it will not be added, if it returns
#                       False for a vanished item, that item is kept
def automation_discovery(
    *,
    config_cache: ConfigCache,
    host_config: HostConfig,
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

    cmk.core_helpers.cache.FileCacheGlobals.use_outdated = True
    cmk.core_helpers.cache.FileCacheGlobals.maybe = use_cached_snmp_data

    try:
        # in "refresh" mode we first need to remove all previously discovered
        # checks of the host, so that _get_host_services() does show us the
        # new discovered check parameters.
        if mode is DiscoveryMode.REFRESH:
            result.self_removed += host_config.remove_autochecks()  # this is cluster-aware!

        ipaddress = (
            None if config_cache.is_cluster(host_name) else config.lookup_ip_address(host_config)
        )

        fetched: Sequence[
            Tuple[SourceInfo, Result[AgentRawData | SNMPRawData, Exception], Snapshot]
        ] = fetch_all(
            make_sources(
                host_config,
                ipaddress,
                ip_lookup=lambda host_name: config.lookup_ip_address(
                    config_cache.get_host_config(host_name)
                ),
                selected_sections=NO_SELECTION,
                force_snmp_cache_refresh=not use_cached_snmp_data,
                on_scan_error=on_error,
                simulation_mode=config.simulation_mode,
                missing_sys_description=config.get_config_cache().in_binary_hostlist(
                    host_name, config.snmp_without_sys_descr
                ),
                file_cache_max_age=max_cachefile_age,
            ),
            mode=Mode.DISCOVERY,
        )
        host_sections, _results = parse_messages(
            ((f[0], f[1]) for f in fetched),
            selected_sections=NO_SELECTION,
            logger=logging.getLogger("cmk.base.discovery"),
        )
        store_piggybacked_sections(host_sections)
        parsed_sections_broker = make_broker(host_sections)

        if mode is not DiscoveryMode.REMOVE:
            host_labels = analyse_host_labels(
                host_name=host_name,
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


def _get_host_services(
    host_config: HostConfig,
    parsed_sections_broker: ParsedSectionsBroker,
    on_error: OnError,
) -> ServicesByTransition:
    config_cache = config.get_config_cache()

    host_name = host_config.hostname
    services: ServicesTable[_Transition]
    if config_cache.is_cluster(host_name):
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
                host_name=host_name,
                parsed_sections_broker=parsed_sections_broker,
                on_error=on_error,
                host_of_clustered_service=config.get_config_cache().host_of_clustered_service,
            )
        }

    services.update(_reclassify_disabled_items(host_name, services))

    # remove the ones shadowed by enforced services
    enforced_services = host_config.enforced_services_table()
    return _group_by_transition({k: v for k, v in services.items() if k not in enforced_services})


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


def discover_marked_hosts(
    core: MonitoringCore,
    autodiscovery_queue: AutoQueue,
) -> None:
    """Autodiscovery"""

    config_cache = config.get_config_cache()

    autodiscovery_queue.cleanup(
        valid_hosts=config_cache.all_configured_hosts(),
        logger=console.verbose,
    )

    if (oldest_queued := autodiscovery_queue.oldest()) is None:
        console.verbose("Autodiscovery: No hosts marked by discovery check\n")
        return
    console.verbose("Autodiscovery: Discovering all hosts marked by discovery check:\n")

    process_hosts = EVERYTHING if (up_hosts := get_up_hosts()) is None else up_hosts

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
    with config.set_use_core_config(
        autochecks_dir=Path(cmk.utils.paths.base_autochecks_dir),
        discovered_host_labels_dir=cmk.utils.paths.base_discovered_host_labels_dir,
    ):
        try:
            _config_cache.clear_all()
            config.get_config_cache().initialize()

            # reset these to their original value to create a correct config
            cmk.core_helpers.cache.FileCacheGlobals.use_outdated = False
            cmk.core_helpers.cache.FileCacheGlobals.maybe = True
            if config.monitoring_core == "cmc":
                cmk.base.core.do_reload(
                    core,
                    locking_mode=config.restart_locking,
                    duplicates=config.duplicate_hosts(),
                )
            else:
                cmk.base.core.do_restart(
                    core,
                    locking_mode=config.restart_locking,
                    duplicates=config.duplicate_hosts(),
                )
        finally:
            _config_cache.clear_all()
            config.get_config_cache().initialize()


def _discover_marked_host(
    *,
    config_cache: ConfigCache,
    host_config: HostConfig,
    autodiscovery_queue: AutoQueue,
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
def get_host_services(
    host_config: HostConfig,
    parsed_sections_broker: ParsedSectionsBroker,
    on_error: OnError,
) -> ServicesByTransition:
    config_cache = config.get_config_cache()

    host_name = host_config.hostname
    services: ServicesTable[_Transition]
    if config_cache.is_cluster(host_name):
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
                host_name=host_name,
                parsed_sections_broker=parsed_sections_broker,
                on_error=on_error,
                host_of_clustered_service=config_cache.host_of_clustered_service,
            )
        }

    services.update(_reclassify_disabled_items(host_name, services))

    # remove the ones shadowed by enforced services
    enforced_services = host_config.enforced_services_table()
    return _group_by_transition({k: v for k, v in services.items() if k not in enforced_services})


# Do the actual work for a non-cluster host or node
def _get_node_services(
    host_name: HostName,
    parsed_sections_broker: ParsedSectionsBroker,
    on_error: OnError,
    host_of_clustered_service: Callable[[HostName, ServiceName], HostName],
) -> ServicesTable[_Transition]:

    service_result = analyse_discovered_services(
        host_name=host_name,
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
                host_name=host_name,
                cluster_name=host_of_clustered_service(host_name, service_name),
                check_plugin_name=entry.check_plugin_name,
                service_name=service_name,
            ),
            entry,
            [host_name],
        )
        for check_source, entry in service_result.chain_with_qualifier()
        if (service_name := config.service_description(host_name, *entry.id()))
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
    host_config: HostConfig,
    parsed_sections_broker: ParsedSectionsBroker,
    on_error: OnError,
) -> ServicesTable[_Transition]:
    config_cache = config.get_config_cache()
    host_name = host_config.hostname
    nodes = config_cache.nodes_of(host_name)
    if not nodes:
        return {}

    cluster_items: ServicesTable[_BasicTransition] = {}
    config_cache = config.get_config_cache()

    # Get services of the nodes. We are only interested in "old", "new" and "vanished"
    # From the states and parameters of these we construct the final state per service.
    for node in nodes:
        entries = analyse_discovered_services(
            host_name=node,
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
                    host_name=host_name,
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
