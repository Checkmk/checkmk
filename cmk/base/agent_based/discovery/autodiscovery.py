#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Callable, Iterable, Mapping
from typing import assert_never, Literal, TypeVar, Union

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.auto_queue import AutoQueue
from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.exceptions import MKGeneralException, MKTimeout, OnError
from cmk.utils.hostaddress import HostName
from cmk.utils.labels import DiscoveredHostLabelsStore, HostLabel
from cmk.utils.log import console, section
from cmk.utils.sectionname import SectionMap
from cmk.utils.servicename import ServiceName

from cmk.checkengine import (
    FetcherFunction,
    filter_out_errors,
    HostKey,
    ParserFunction,
    SectionPlugin,
    SummarizerFunction,
)
from cmk.checkengine.check_table import ServiceID
from cmk.checkengine.checking import CheckPluginName, Item
from cmk.checkengine.discovery import (
    analyse_services,
    AutocheckEntry,
    AutocheckServiceWithNodes,
    AutochecksStore,
    discover_host_labels,
    discover_services,
    DiscoveryMode,
    DiscoveryPlugin,
    DiscoveryResult,
    find_plugins,
    HostLabelPlugin,
    QualifiedDiscovery,
)
from cmk.checkengine.discovery.filters import RediscoveryParameters
from cmk.checkengine.discovery.filters import ServiceFilters as _ServiceFilters
from cmk.checkengine.sectionparser import make_providers, Provider, store_piggybacked_sections

from cmk.base.config import ConfigCache

__all__ = ["get_host_services"]

_BasicTransition = Literal["old", "new", "vanished"]
_Transition = Union[
    _BasicTransition,
    Literal["ignored", "clustered_old", "clustered_new", "clustered_vanished", "clustered_ignored"],
]


_L = TypeVar("_L", bound=str)

ServicesTableEntry = tuple[_L, AutocheckEntry, list[HostName]]
ServicesTable = dict[ServiceID, ServicesTableEntry[_L]]
ServicesByTransition = dict[_Transition, list[AutocheckServiceWithNodes]]


# determine changed services on host.
# param mode: can be one of "new", "remove", "fixall", "refresh", "only-host-labels"
# param servic_filter: if a filter is set, it controls whether items are touched by the discovery.
#                       if it returns False for a new item it will not be added, if it returns
#                       False for a vanished item, that item is kept
def automation_discovery(
    host_name: HostName,
    *,
    config_cache: ConfigCache,
    parser: ParserFunction,
    fetcher: FetcherFunction,
    summarizer: SummarizerFunction,
    section_plugins: SectionMap[SectionPlugin],
    host_label_plugins: SectionMap[HostLabelPlugin],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    get_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
    mode: DiscoveryMode,
    keep_clustered_vanished_services: bool,
    service_filters: _ServiceFilters | None,
    on_error: OnError,
) -> DiscoveryResult:
    console.verbose("  Doing discovery with mode '%s'...\n" % mode)
    result = DiscoveryResult()
    if host_name not in config_cache.all_active_hosts():
        result.error_text = ""
        return result

    try:
        # in "refresh" mode we first need to remove all previously discovered
        # checks of the host, so that _get_host_services() does show us the
        # new discovered check parameters.
        if mode is DiscoveryMode.REFRESH:
            result.self_removed += config_cache.remove_autochecks(
                host_name
            )  # this is cluster-aware!

        fetched = fetcher(host_name, ip_address=None)
        host_sections = parser((f[0], f[1]) for f in fetched)
        if failed_sources_results := [r for r in summarizer(host_sections) if r.state != 0]:
            return DiscoveryResult(error_text=", ".join(r.summary for r in failed_sources_results))

        host_sections_no_error = filter_out_errors(
            (HostKey(s.hostname, s.source_type), r.ok) for s, r in host_sections if r.is_ok()
        )
        store_piggybacked_sections(host_sections_no_error)
        providers = make_providers(host_sections_no_error, section_plugins)

        if mode is not DiscoveryMode.REMOVE:
            host_labels = QualifiedDiscovery[HostLabel](
                preexisting=DiscoveredHostLabelsStore(host_name).load(),
                current=discover_host_labels(
                    host_name,
                    host_label_plugins,
                    providers=providers,
                    on_error=on_error,
                ),
            )
            result.self_new_host_labels = len(host_labels.new)
            result.self_total_host_labels = len(host_labels.present)

            DiscoveredHostLabelsStore(host_name).save(host_labels.kept())
            if host_labels.new or host_labels.vanished:  # add 'changed' once it exists.
                # Rulesets for service discovery can match based on the hosts labels.
                config_cache.ruleset_matcher.clear_caches()

            if mode is DiscoveryMode.ONLY_HOST_LABELS:
                result.diff_text = _make_diff(host_labels.vanished, host_labels.new, (), ())
                return result
        else:
            host_labels = QualifiedDiscovery.empty()

        # Compute current state of new and existing checks
        services = get_host_services(
            host_name,
            config_cache=config_cache,
            providers=providers,
            plugins=plugins,
            get_service_description=get_service_description,
            on_error=on_error,
        )

        old_services = {x.service.id(): x for x in services.get("old", [])}

        # Create new list of checks
        final_services = _get_post_discovery_autocheck_services(
            host_name,
            services,
            service_filters or _ServiceFilters.accept_all(),
            result,
            get_service_description,
            mode,
            keep_clustered_vanished_services,
        )
        config_cache.set_autochecks(host_name, list(final_services.values()))

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
    get_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
    mode: DiscoveryMode,
    keep_clustered_vanished_services: bool,
) -> Mapping[ServiceID, AutocheckServiceWithNodes]:
    """
    The output contains a selection of services in the states "new", "old", "ignored", "vanished"
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
                    if service_filters.new(get_service_description(host_name, *s.service.id()))
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
                    get_service_description(host_name, *entry.service.id())
                ):
                    result.self_removed += 1
                else:
                    post_discovery_services[entry.service.id()] = entry
                    result.self_kept += 1

        else:
            if check_source != "clustered_vanished" or keep_clustered_vanished_services:
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
    services_vanished: Iterable[AutocheckEntry],
    services_new: Iterable[AutocheckEntry],
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


def autodiscovery(
    host_name: HostName,
    *,
    config_cache: ConfigCache,
    fetcher: FetcherFunction,
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    section_plugins: SectionMap[SectionPlugin],
    host_label_plugins: SectionMap[HostLabelPlugin],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    get_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
    schedule_discovery_check: Callable[[HostName], object],
    rediscovery_parameters: RediscoveryParameters,
    invalidate_host_config: Callable[[], object],
    autodiscovery_queue: AutoQueue,
    reference_time: float,
    oldest_queued: float,
    on_error: OnError,
) -> tuple[DiscoveryResult | None, bool]:
    reason = _may_rediscover(
        rediscovery_parameters=rediscovery_parameters,
        reference_time=reference_time,
        oldest_queued=oldest_queued,
    )
    if reason:
        console.verbose(f"  skipped: {reason}\n")
        return None, False

    result = automation_discovery(
        host_name,
        config_cache=config_cache,
        parser=parser,
        fetcher=fetcher,
        summarizer=summarizer,
        section_plugins=section_plugins,
        host_label_plugins=host_label_plugins,
        plugins=plugins,
        get_service_description=get_service_description,
        mode=DiscoveryMode(rediscovery_parameters.get("mode")),
        keep_clustered_vanished_services=rediscovery_parameters.get(
            "keep_clustered_vanished_services", True
        ),
        service_filters=_ServiceFilters.from_settings(rediscovery_parameters),
        on_error=on_error,
    )
    if result.error_text is not None:
        # for offline hosts the error message is empty. This is to remain
        # compatible with the automation code
        console.verbose(f"  failed: {result.error_text or 'host is offline'}\n")
        # delete the file even in error case, otherwise we might be causing the same error
        # every time the cron job runs
        (autodiscovery_queue.path / str(host_name)).unlink(missing_ok=True)
        return None, False

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
        activation_required = bool(rediscovery_parameters["activation"])

        # Enforce base code creating a new host config object after this change
        invalidate_host_config()

        # Now ensure that the discovery service is updated right after the changes
        schedule_discovery_check(host_name)

    (autodiscovery_queue.path / str(host_name)).unlink(missing_ok=True)

    return (result, activation_required) if something_changed else (None, False)


def _may_rediscover(
    rediscovery_parameters: RediscoveryParameters,
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
    host_name: HostName,
    *,
    config_cache: ConfigCache,
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    providers: Mapping[HostKey, Provider],
    get_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
    on_error: OnError,
) -> ServicesByTransition:
    services: ServicesTable[_Transition]
    if config_cache.is_cluster(host_name):
        services = {
            **_get_cluster_services(
                host_name,
                config_cache=config_cache,
                providers=providers,
                plugins=plugins,
                get_service_description=get_service_description,
                on_error=on_error,
            )
        }
    else:
        services = {
            **_get_node_services(
                config_cache,
                host_name,
                providers=providers,
                plugins=plugins,
                on_error=on_error,
                get_effective_host=config_cache.effective_host,
                get_service_description=get_service_description,
            )
        }

    services.update(
        _reclassify_disabled_items(config_cache, host_name, services, get_service_description)
    )

    # remove the ones shadowed by enforced services
    enforced_services = config_cache.enforced_services_table(host_name)
    return _group_by_transition({k: v for k, v in services.items() if k not in enforced_services})


# Do the actual work for a non-cluster host or node
def _get_node_services(
    config_cache: ConfigCache,
    host_name: HostName,
    *,
    providers: Mapping[HostKey, Provider],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    on_error: OnError,
    get_effective_host: Callable[[HostName, ServiceName], HostName],
    get_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
) -> ServicesTable[_Transition]:
    candidates = find_plugins(
        providers,
        [(plugin_name, plugin.sections) for plugin_name, plugin in plugins.items()],
    )
    skip = {
        plugin_name
        for plugin_name in candidates
        if config_cache.check_plugin_ignored(host_name, plugin_name)
    }

    section.section_step("Executing discovery plugins (%d)" % len(candidates))
    console.vverbose("  Trying discovery with: %s\n" % ", ".join(str(n) for n in candidates))
    # The host name must be set for the host_name() calls commonly used to determine the
    # host name for host_extra_conf{_merged,} calls in the legacy checks.

    for plugin_name in skip:
        console.vverbose(f"  Skip ignored check plugin name {plugin_name!r}\n")

    autocheck_store = AutochecksStore(host_name)
    try:
        discovered_services = discover_services(
            host_name, candidates - skip, providers=providers, plugins=plugins, on_error=on_error
        )
    except KeyboardInterrupt:
        raise MKGeneralException("Interrupted by Ctrl-C.")

    service_result = analyse_services(
        existing_services=autocheck_store.read(),
        discovered_services=discovered_services,
        run_plugin_names=EVERYTHING,
        forget_existing=False,
        keep_vanished=False,
    )
    return make_table(
        config_cache,
        host_name,
        service_result,
        get_effective_host=get_effective_host,
        get_service_description=get_service_description,
    )


def make_table(
    config_cache: ConfigCache,
    host_name: HostName,
    entries: QualifiedDiscovery[AutocheckEntry],
    *,
    get_effective_host: Callable[[HostName, ServiceName], HostName],
    get_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
) -> ServicesTable[_Transition]:
    return {
        entry.id(): (
            _node_service_source(
                config_cache,
                host_name,
                check_source=check_source,
                cluster_name=get_effective_host(host_name, service_name),
                check_plugin_name=entry.check_plugin_name,
                service_name=service_name,
            ),
            entry,
            [host_name],
        )
        for check_source, entry in entries.chain_with_qualifier()
        if (service_name := get_service_description(host_name, *entry.id()))
    }


def _node_service_source(
    config_cache: ConfigCache,
    host_name: HostName,
    *,
    check_source: _BasicTransition,
    cluster_name: HostName,
    check_plugin_name: CheckPluginName,
    service_name: ServiceName,
) -> _Transition:
    if host_name == cluster_name:
        return check_source

    if config_cache.service_ignored(
        cluster_name, service_name
    ) or config_cache.check_plugin_ignored(cluster_name, check_plugin_name):
        return "ignored"

    if check_source == "vanished":
        return "clustered_vanished"
    if check_source == "old":
        return "clustered_old"
    return "clustered_new"


def _reclassify_disabled_items(
    config_cache: ConfigCache,
    host_name: HostName,
    services: ServicesTable[_Transition],
    get_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
) -> Iterable[tuple[ServiceID, ServicesTableEntry]]:
    """Handle disabled services -> 'ignored'"""
    yield from (
        (service.id(), ("ignored", service, [host_name]))
        for check_source, service, _found_on_nodes in services.values()
        if config_cache.service_ignored(
            host_name, get_service_description(host_name, *service.id())
        )
        or config_cache.check_plugin_ignored(host_name, service.check_plugin_name)
    )


def _group_by_transition(
    transition_services: ServicesTable[_Transition],
) -> ServicesByTransition:
    services_by_transition: ServicesByTransition = {}
    for transition, service, found_on_nodes in transition_services.values():
        services_by_transition.setdefault(
            transition,
            [],
        ).append(AutocheckServiceWithNodes(service, found_on_nodes))
    return services_by_transition


def _get_cluster_services(
    host_name: HostName,
    *,
    config_cache: ConfigCache,
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    providers: Mapping[HostKey, Provider],
    get_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
    on_error: OnError,
) -> ServicesTable[_Transition]:
    nodes = config_cache.nodes_of(host_name)
    if not nodes:
        return {}

    cluster_items: ServicesTable[_BasicTransition] = {}

    # Get services of the nodes. We are only interested in "old", "new" and "vanished"
    # From the states and parameters of these we construct the final state per service.
    for node in nodes:
        candidates = find_plugins(
            # This call doesn't seem to depend on `node` so we could
            # probably take it out of the loop to improve readability
            # and performance.
            providers,
            [(plugin_name, plugin.sections) for plugin_name, plugin in plugins.items()],
        )
        skip = {
            plugin_name
            for plugin_name in candidates
            if config_cache.check_plugin_ignored(host_name, plugin_name)
        }
        section.section_step("Executing discovery plugins (%d)" % len(candidates))
        console.vverbose("  Trying discovery with: %s\n" % ", ".join(str(n) for n in candidates))

        for plugin_name in skip:
            console.vverbose(f"  Skip ignored check plugin name {plugin_name!r}\n")

        autocheck_store = AutochecksStore(node)
        discovered_services = discover_services(
            node,
            candidates - skip,
            providers=providers,
            plugins=plugins,
            on_error=on_error,
        )
        entries = analyse_services(
            existing_services=autocheck_store.read(),
            discovered_services=discovered_services,
            run_plugin_names=EVERYTHING,
            forget_existing=False,
            keep_vanished=False,
        )
        for check_source, entry in entries.chain_with_qualifier():
            cluster_items.update(
                _cluster_service_entry(
                    check_source=check_source,
                    host_name=host_name,
                    node_name=node,
                    services_cluster=config_cache.effective_host(
                        node, get_service_description(node, *entry.id())
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
    entry: AutocheckEntry,
    existing_entry: ServicesTableEntry[_BasicTransition] | None,
) -> Iterable[tuple[ServiceID, ServicesTableEntry[_BasicTransition]]]:
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
