#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import dataclasses
import itertools
import time
from collections.abc import Callable, Container, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never, Generic, Literal, TypeVar

import cmk.utils.debug
from cmk.utils.auto_queue import AutoQueue
from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.exceptions import MKGeneralException, MKTimeout, OnError
from cmk.utils.hostaddress import HostName
from cmk.utils.labels import DiscoveredHostLabelsStore, HostLabel
from cmk.utils.log import console, section
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher
from cmk.utils.sectionname import SectionMap, SectionName
from cmk.utils.servicename import Item, ServiceName

from cmk.checkengine.checking import CheckPluginName, ServiceID
from cmk.checkengine.fetcher import FetcherFunction, HostKey
from cmk.checkengine.parser import group_by_host, ParserFunction
from cmk.checkengine.sectionparser import (
    make_providers,
    Provider,
    SectionPlugin,
    store_piggybacked_sections,
)
from cmk.checkengine.summarize import SummarizerFunction

from ._autochecks import (
    AutocheckEntry,
    AutocheckServiceWithNodes,
    AutochecksStore,
    DiscoveredService,
    remove_autochecks_of_host,
    set_autochecks_of_cluster,
    set_autochecks_of_real_hosts,
)
from ._discovery import DiscoveryPlugin
from ._filters import RediscoveryParameters
from ._filters import ServiceFilters as _ServiceFilters
from ._host_labels import discover_host_labels, HostLabelPlugin
from ._services import analyse_services, discover_services, find_plugins
from ._utils import DiscoveredItem, DiscoverySettings, QualifiedDiscovery

__all__ = ["get_host_services"]


@dataclass
class DiscoveryResult:
    self_new: int = 0
    self_changed: int = 0
    self_removed: int = 0
    self_kept: int = 0
    self_total: int = 0
    self_new_host_labels: int = 0
    self_total_host_labels: int = 0
    clustered_new: int = 0
    clustered_old: int = 0
    clustered_vanished: int = 0
    clustered_ignored: int = 0

    # None  -> No error occured
    # ""    -> Not monitored (disabled host)
    # "..." -> An error message about the failed discovery
    error_text: str | None = None

    # An optional text to describe the services changed by the operation
    diff_text: str | None = None


_BasicTransition = Literal["changed", "unchanged", "new", "vanished"]
_Transition = (
    _BasicTransition
    | Literal[
        "ignored",
        "clustered_old",
        "clustered_new",
        "clustered_vanished",
        "clustered_ignored",
    ]
)


_L = TypeVar("_L", bound=str)


@dataclasses.dataclass
class ServicesTableEntry(Generic[_L]):
    transition: _L
    autocheck: DiscoveredItem[AutocheckEntry]
    hosts: list[HostName]


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
    is_cluster: bool,
    cluster_nodes: Sequence[HostName],
    active_hosts: Container[HostName],
    ruleset_matcher: RulesetMatcher,
    parser: ParserFunction,
    fetcher: FetcherFunction,
    summarizer: SummarizerFunction,
    section_plugins: SectionMap[SectionPlugin],
    host_label_plugins: SectionMap[HostLabelPlugin],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    ignore_service: Callable[[HostName, ServiceName], bool],
    ignore_plugin: Callable[[HostName, CheckPluginName], bool],
    get_effective_host: Callable[[HostName, ServiceName], HostName],
    get_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
    settings: DiscoverySettings,
    keep_clustered_vanished_services: bool,
    service_filters: _ServiceFilters | None,
    enforced_services: Container[ServiceID],
    on_error: OnError,
    section_error_handling: Callable[[SectionName, Sequence[object]], str],
) -> DiscoveryResult:
    console.verbose("  Doing discovery with '%r'...\n" % settings)
    result = DiscoveryResult()
    if host_name not in active_hosts:
        result.error_text = ""
        return result

    service_changes_requested = (
        settings.add_new_services
        or settings.remove_vanished_services
        or settings.update_changed_service_labels
        or settings.update_changed_service_parameters
    )

    try:
        # in "refresh" mode we first need to remove all previously discovered
        # checks of the host, so that _get_host_services() does show us the
        # new discovered check parameters.
        # this is a weird way of updating changed services:
        # forgetting the old onces, add adding changed ones, that now appear to be "new"
        if settings.update_changed_service_labels and settings.update_changed_service_parameters:
            result.self_removed += sum(
                # this is cluster-aware!
                remove_autochecks_of_host(
                    node, host_name, get_effective_host, get_service_description
                )
                for node in (cluster_nodes if is_cluster else [host_name])
            )

        fetched = fetcher(host_name, ip_address=None)
        host_sections = parser((f[0], f[1]) for f in fetched)
        if failed_sources_results := [r for r in summarizer(host_sections) if r.state != 0]:
            return DiscoveryResult(error_text=", ".join(r.summary for r in failed_sources_results))

        host_sections_by_host = group_by_host(
            (HostKey(s.hostname, s.source_type), r.ok) for s, r in host_sections if r.is_ok()
        )
        store_piggybacked_sections(host_sections_by_host)
        providers = make_providers(
            host_sections_by_host,
            section_plugins,
            error_handling=section_error_handling,
        )

        if settings.update_host_labels:
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

            DiscoveredHostLabelsStore(host_name).save(host_labels.present)
            if host_labels.new or host_labels.vanished:  # add 'changed' once it exists.
                # Rulesets for service discovery can match based on the hosts labels.
                ruleset_matcher.clear_caches()

            if not service_changes_requested:
                result.diff_text = _make_diff(host_labels.vanished, host_labels.new, (), ())
                return result
        else:
            host_labels = QualifiedDiscovery.empty()

        # Compute current state of new and existing checks
        services = get_host_services(
            host_name,
            is_cluster=is_cluster,
            cluster_nodes=cluster_nodes,
            providers=providers,
            plugins=plugins,
            ignore_service=ignore_service,
            ignore_plugin=ignore_plugin,
            get_effective_host=get_effective_host,
            get_service_description=get_service_description,
            enforced_services=enforced_services,
            on_error=on_error,
        )

        existing_services = {
            DiscoveredService.id(x.service): x
            for x in itertools.chain(
                services.get("changed", []),
                services.get("unchanged", []),
            )
        }

        # Create new list of checks
        final_services = _get_post_discovery_autocheck_services(
            host_name,
            services,
            service_filters or _ServiceFilters.accept_all(),
            result,
            get_service_description,
            settings,
            keep_clustered_vanished_services,
        )
        new_services = list(final_services.values())
        if is_cluster:
            set_autochecks_of_cluster(
                cluster_nodes,
                host_name,
                new_services,
                get_effective_host,
                get_service_description,
            )
        else:
            set_autochecks_of_real_hosts(host_name, new_services)

        result.diff_text = _make_diff(
            host_labels.vanished,
            host_labels.new,
            (
                x.service
                for x in existing_services.values()
                if DiscoveredService.id(x.service) not in final_services
            ),
            (
                x.service
                for x in final_services.values()
                if DiscoveredService.id(x.service) not in existing_services
            ),
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
    settings: DiscoverySettings,
    keep_clustered_vanished_services: bool,
) -> Mapping[ServiceID, AutocheckServiceWithNodes]:
    """
    The output contains a selection of services in the states "new", "unchanged", "changed",
     "ignored", "vanished" (depending on the value of `mode`) and "clusterd_".

    Service in with the state "custom", "active" and "manual" are currently not checked.

    Note:

        Discovered services that are shadowed by enforces services will vanish that way.

    """
    post_discovery_services = {}
    for check_transition, discovered_services_with_nodes in services.items():
        if check_transition == "new":
            if settings.add_new_services:
                new = {
                    DiscoveredService.id(s.service): s
                    for s in discovered_services_with_nodes
                    if service_filters.new(
                        get_service_description(host_name, *DiscoveredService.id(s.service))
                    )
                }
                result.self_new += len(new)
                post_discovery_services.update(new)

        elif (  # pylint: disable=consider-using-in
            check_transition == "unchanged" or check_transition == "ignored"
        ):
            # keep currently existing valid services in any case
            post_discovery_services.update(
                (DiscoveredService.id(s.service), s) for s in discovered_services_with_nodes
            )
            result.self_kept += len(discovered_services_with_nodes)

        elif check_transition == "changed":
            for entry in discovered_services_with_nodes:
                service = entry.service
                assert service.previous is not None and service.new is not None
                new_entry = AutocheckServiceWithNodes(
                    service=DiscoveredItem[AutocheckEntry](
                        new=AutocheckEntry(
                            check_plugin_name=DiscoveredService.check_plugin_name(service),
                            item=DiscoveredService.item(service),
                            parameters=(
                                service.new.parameters
                                if settings.update_changed_service_parameters
                                else service.previous.parameters
                            ),
                            service_labels=(
                                service.new.service_labels
                                if settings.update_changed_service_labels
                                else service.previous.service_labels
                            ),
                        ),
                        previous=service.previous,
                    ),
                    nodes=entry.nodes,
                )
                post_discovery_services[DiscoveredService.id(service)] = new_entry
                if new_entry.service.new != new_entry.service.previous:
                    result.self_changed += 1
                else:
                    result.self_kept += 1

        elif check_transition == "vanished":
            # keep item, if we are currently only looking for new services
            # otherwise fix it: remove ignored and non-longer existing services
            for entry in discovered_services_with_nodes:
                if settings.remove_vanished_services and service_filters.vanished(
                    get_service_description(host_name, *DiscoveredService.id(entry.service))
                ):
                    result.self_removed += 1
                else:
                    post_discovery_services[DiscoveredService.id(entry.service)] = entry

                    result.self_kept += 1

        else:
            if check_transition != "clustered_vanished" or keep_clustered_vanished_services:
                # Silently keep clustered services
                post_discovery_services.update(
                    (DiscoveredService.id(s.service), s) for s in discovered_services_with_nodes
                )
            if check_transition == "clustered_new":
                result.clustered_new += len(discovered_services_with_nodes)
            elif check_transition == "clustered_old":
                result.clustered_old += len(discovered_services_with_nodes)
            elif check_transition == "clustered_vanished":
                result.clustered_vanished += len(discovered_services_with_nodes)
            elif check_transition == "clustered_ignored":
                result.clustered_ignored += len(discovered_services_with_nodes)
            else:
                assert_never(check_transition)

    return post_discovery_services


def _make_diff(
    labels_vanished: Iterable[HostLabel],
    labels_new: Iterable[HostLabel],
    services_vanished: Iterable[DiscoveredItem[AutocheckEntry]],
    services_new: Iterable[DiscoveredItem[AutocheckEntry]],
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
                        f"Removed service: Check plug-in '{DiscoveredService.check_plugin_name(s)}'."
                        if DiscoveredService.item(s) is None
                        else f"Removed service: Check plug-in '{DiscoveredService.check_plugin_name(s)}' / item '{DiscoveredService.item(s)}'."
                    )
                    for s in services_vanished
                ),
                *(
                    (
                        f"Added service: Check plug-in '{DiscoveredService.check_plugin_name(s)}'."
                        if DiscoveredService.item(s) is None
                        else f"Added service: Check plug-in '{DiscoveredService.check_plugin_name(s)}' / item '{DiscoveredService.item(s)}'."
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
    is_cluster: bool,
    cluster_nodes: Sequence[HostName],
    active_hosts: Container[HostName],
    ruleset_matcher: RulesetMatcher,
    fetcher: FetcherFunction,
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    section_plugins: SectionMap[SectionPlugin],
    section_error_handling: Callable[[SectionName, Sequence[object]], str],
    host_label_plugins: SectionMap[HostLabelPlugin],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    ignore_service: Callable[[HostName, ServiceName], bool],
    ignore_plugin: Callable[[HostName, CheckPluginName], bool],
    get_effective_host: Callable[[HostName, ServiceName], HostName],
    get_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
    schedule_discovery_check: Callable[[HostName], object],
    rediscovery_parameters: RediscoveryParameters,
    invalidate_host_config: Callable[[], object],
    autodiscovery_queue: AutoQueue,
    reference_time: float,
    oldest_queued: float,
    enforced_services: Container[ServiceID],
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
        is_cluster=is_cluster,
        cluster_nodes=cluster_nodes,
        active_hosts=active_hosts,
        ruleset_matcher=ruleset_matcher,
        parser=parser,
        fetcher=fetcher,
        summarizer=summarizer,
        section_plugins=section_plugins,
        section_error_handling=section_error_handling,
        host_label_plugins=host_label_plugins,
        plugins=plugins,
        ignore_service=ignore_service,
        ignore_plugin=ignore_plugin,
        get_effective_host=get_effective_host,
        get_service_description=get_service_description,
        settings=DiscoverySettings.from_vs(rediscovery_parameters.get("mode")),
        keep_clustered_vanished_services=rediscovery_parameters.get(
            "keep_clustered_vanished_services", True
        ),
        service_filters=_ServiceFilters.from_settings(rediscovery_parameters),
        enforced_services=enforced_services,
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
        or result.self_changed != 0
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
            f"{result.self_kept} kept, {result.self_changed} changed, "
            f"{result.self_total} total services "
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
#    "unchanged"     : Check is discovered and already monitored (most common)
#    "changed"       : Check is discovered and already monitored but changed
#    "vanished"      : Check had been discovered previously, but item has vanished
#    "ignored"       : discovered or static, but disabled via ignored_services
#    "clustered_new" : New service found on a node that belongs to a cluster
#    "clustered_old" : Old service found on a node that belongs to a cluster
# This function is cluster-aware
def get_host_services(
    host_name: HostName,
    *,
    is_cluster: bool,
    cluster_nodes: Iterable[HostName],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    providers: Mapping[HostKey, Provider],
    ignore_service: Callable[[HostName, ServiceName], bool],
    ignore_plugin: Callable[[HostName, CheckPluginName], bool],
    get_effective_host: Callable[[HostName, ServiceName], HostName],
    get_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
    enforced_services: Container[ServiceID],
    on_error: OnError,
) -> ServicesByTransition:
    services: ServicesTable[_Transition]
    if is_cluster:
        services = {
            **_get_cluster_services(
                host_name,
                cluster_nodes=cluster_nodes,
                providers=providers,
                plugins=plugins,
                ignore_plugin=ignore_plugin,
                get_effective_host=get_effective_host,
                get_service_description=get_service_description,
                on_error=on_error,
            )
        }
    else:
        services = {
            **_get_node_services(
                host_name,
                providers=providers,
                plugins=plugins,
                on_error=on_error,
                ignore_service=ignore_service,
                ignore_plugin=ignore_plugin,
                get_effective_host=get_effective_host,
                get_service_description=get_service_description,
            )
        }

    services.update(
        _reclassify_disabled_items(
            host_name,
            services,
            ignore_service,
            ignore_plugin,
            get_service_description,
        )
    )

    # remove the ones shadowed by enforced services
    return _group_by_transition({k: v for k, v in services.items() if k not in enforced_services})


# Do the actual work for a non-cluster host or node
def _get_node_services(
    host_name: HostName,
    *,
    providers: Mapping[HostKey, Provider],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    on_error: OnError,
    ignore_service: Callable[[HostName, ServiceName], bool],
    ignore_plugin: Callable[[HostName, CheckPluginName], bool],
    get_effective_host: Callable[[HostName, ServiceName], HostName],
    get_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
) -> ServicesTable[_Transition]:
    candidates = find_plugins(
        providers,
        [(plugin_name, plugin.sections) for plugin_name, plugin in plugins.items()],
    )
    skip = {plugin_name for plugin_name in candidates if ignore_plugin(host_name, plugin_name)}

    section.section_step("Executing discovery plugins (%d)" % len(candidates))
    console.vverbose("  Trying discovery with: %s\n" % ", ".join(str(n) for n in candidates))
    # The host name must be set for the host_name() calls commonly used to determine the
    # host name for get_host_values{_merged,} calls in the legacy checks.

    for plugin_name in skip:
        console.vverbose(f"  Skip ignored check plug-in name {plugin_name!r}\n")

    autocheck_store = AutochecksStore(host_name)
    try:
        discovered_services = discover_services(
            host_name,
            candidates - skip,
            providers=providers,
            plugins=plugins,
            on_error=on_error,
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
        host_name,
        service_result,
        ignore_service=ignore_service,
        ignore_plugin=ignore_plugin,
        get_effective_host=get_effective_host,
        get_service_description=get_service_description,
    )


def make_table(
    host_name: HostName,
    entries: QualifiedDiscovery[AutocheckEntry],
    *,
    ignore_service: Callable[[HostName, ServiceName], bool],
    ignore_plugin: Callable[[HostName, CheckPluginName], bool],
    get_effective_host: Callable[[HostName, ServiceName], HostName],
    get_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
) -> ServicesTable[_Transition]:
    return {
        DiscoveredService.id(entry): ServicesTableEntry(
            transition=_node_service_source(
                host_name,
                ignore_service=ignore_service,
                ignore_plugin=ignore_plugin,
                check_source=service_transition,
                cluster_name=get_effective_host(host_name, service_name),
                check_plugin_name=DiscoveredService.check_plugin_name(entry),
                service_name=service_name,
            ),
            autocheck=entry,
            hosts=[host_name],
        )
        for service_transition, entry in entries.chain_with_transition()
        if (
            service_name := get_service_description(
                host_name,
                DiscoveredService.check_plugin_name(entry),
                DiscoveredService.item(entry),
            )
        )
    }


def _node_service_source(
    host_name: HostName,
    *,
    ignore_service: Callable[[HostName, ServiceName], bool],
    ignore_plugin: Callable[[HostName, CheckPluginName], bool],
    check_source: _BasicTransition,
    cluster_name: HostName,
    check_plugin_name: CheckPluginName,
    service_name: ServiceName,
) -> _Transition:
    if host_name == cluster_name:
        return check_source

    if ignore_service(cluster_name, service_name) or ignore_plugin(cluster_name, check_plugin_name):
        return "ignored"

    if check_source == "vanished":
        return "clustered_vanished"
    if check_source in ("changed", "unchanged"):
        return "clustered_old"
    return "clustered_new"


def _reclassify_disabled_items(
    host_name: HostName,
    services: ServicesTable[_Transition],
    ignore_service: Callable[[HostName, ServiceName], bool],
    ignore_plugin: Callable[[HostName, CheckPluginName], bool],
    get_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
) -> Iterable[tuple[ServiceID, ServicesTableEntry]]:
    """Handle disabled services -> 'ignored'"""
    yield from (
        (
            DiscoveredService.id(service.autocheck),
            ServicesTableEntry(
                transition="ignored",
                autocheck=service.autocheck,
                hosts=[host_name],
            ),
        )
        for service in services.values()
        if ignore_service(
            host_name,
            get_service_description(host_name, *DiscoveredService.id(service.autocheck)),
        )
        or ignore_plugin(host_name, DiscoveredService.check_plugin_name(service.autocheck))
    )


def _group_by_transition(
    transition_services: ServicesTable[_Transition],
) -> ServicesByTransition:
    services_by_transition: ServicesByTransition = {}
    for service in transition_services.values():
        services_by_transition.setdefault(
            service.transition,
            [],
        ).append(AutocheckServiceWithNodes(service.autocheck, service.hosts))
    return services_by_transition


def _get_cluster_services(
    host_name: HostName,
    *,
    cluster_nodes: Iterable[HostName],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    providers: Mapping[HostKey, Provider],
    ignore_plugin: Callable[[HostName, CheckPluginName], bool],
    get_effective_host: Callable[[HostName, ServiceName], HostName],
    get_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
    on_error: OnError,
) -> ServicesTable[_Transition]:
    cluster_items: ServicesTable[_Transition] = {}  # actually _BasicTransition but typing...

    for node in cluster_nodes:
        candidates = find_plugins(
            # This call doesn't seem to depend on `node` so we could
            # probably take it out of the loop to improve readability
            # and performance.
            providers,
            [(plugin_name, plugin.sections) for plugin_name, plugin in plugins.items()],
        )
        skip = {plugin_name for plugin_name in candidates if ignore_plugin(host_name, plugin_name)}
        section.section_step("Executing discovery plugins (%d)" % len(candidates))
        console.vverbose("  Trying discovery with: %s\n" % ", ".join(str(n) for n in candidates))

        for plugin_name in skip:
            console.vverbose(f"  Skip ignored check plug-in name {plugin_name!r}\n")

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
        for check_source, entry in entries.chain_with_transition():
            cluster_items.update(
                _cluster_service_entry(
                    node_transition=check_source,
                    host_name=host_name,
                    node_name=node,
                    services_cluster=get_effective_host(
                        node,
                        get_service_description(node, *DiscoveredService.id(entry)),
                    ),
                    entry=entry,
                    current_recorded_entry=cluster_items.get(DiscoveredService.id(entry)),
                )
            )

    return cluster_items


def _cluster_service_entry(
    *,
    node_transition: _BasicTransition,
    host_name: HostName,
    node_name: HostName,
    services_cluster: HostName,
    entry: DiscoveredItem[AutocheckEntry],
    current_recorded_entry: ServicesTableEntry[_Transition] | None,
) -> Iterable[tuple[ServiceID, ServicesTableEntry[_Transition]]]:
    """
    The purpose of this function is to determine the service transition (and autocheck) in a
    cumulative way by going through all nodes where the service is present

    To keep in mind:
        * the order of the nodes is always the same

    Variables:
        * entry:
            the service representation of the node we are currently investigating
        * current_recorded_entry:
            the cumulative service representation based on all previously iterated nodes

    Example for understanding:
        * cluster consists of 2 nodes: node1 and node2
        * node1 has a service with transition "vanished"
        * node2 has a service with transition "new"
        * the order of nodes is always the same: first we inspect node1 and then node2
        * from a cluster perspective the service is neither new nor vanished
            * vanished assumes that the service existed before in the previous run
            * new assumes that the service does still exist in the current run
            --> from a cluster perspective it is therefore changed/unchanged it only moved from one
            node to another

    """
    if host_name != services_cluster:
        return  # not part of this host

    if current_recorded_entry is None:
        yield (
            DiscoveredService.id(entry),
            ServicesTableEntry(
                transition=node_transition,
                autocheck=entry,
                hosts=[node_name],
            ),
        )
        return

    nodes_with_service = current_recorded_entry.hosts
    if node_name not in nodes_with_service:
        nodes_with_service.append(node_name)

    existing_autocheck_entry = current_recorded_entry.autocheck
    accumulated_transition = current_recorded_entry.transition
    match accumulated_transition, node_transition:
        case "unchanged" | "changed", _not_relevant:
            # unchanged/changed always preconditions a service's preexistence
            return
        case "new", "unchanged" | "changed" | "vanished":
            # turns out the service already existed and is not really new
            # Understanding example:
            # Current run: node1 (new service), node2 (unchanged service --> existed before)
            # --> have to compare new service state to previous state of node2 service due to next
            # run, if we simply take node2 service state (e.g. unchanged), then we potentially jump
            # over any potential changes relative to the next run
            # Next run: node1 (unchanged service), node2 (unchanged service)
            # --> node1 service will be taken (first node appearance wins)
            assert existing_autocheck_entry.new is not None
            assert entry.previous is not None
            yield (
                DiscoveredService.id(entry),
                ServicesTableEntry(
                    transition=(
                        "changed"
                        if _changed_service(existing_autocheck_entry.new, entry.previous)
                        else "unchanged"
                    ),
                    autocheck=DiscoveredItem[AutocheckEntry](
                        new=existing_autocheck_entry.new,
                        previous=entry.previous,
                    ),
                    hosts=nodes_with_service,
                ),
            )
        case "new", "new":
            # still new, first new node appearance wins so we keep the existing entry
            return
        case "vanished", "unchanged" | "changed" | "new":
            # turns out the service is not vanished but moved to another node or was already
            # present before
            assert current_recorded_entry.autocheck.previous is not None
            assert entry.new is not None
            yield (
                DiscoveredService.id(entry),
                ServicesTableEntry(
                    transition=(
                        "changed"
                        if _changed_service(current_recorded_entry.autocheck.previous, entry.new)
                        else "unchanged"
                    ),
                    autocheck=DiscoveredItem[AutocheckEntry](
                        new=entry.new,
                        previous=current_recorded_entry.autocheck.previous,
                    ),
                    hosts=nodes_with_service,
                ),
            )
        case "vanished", "vanished":
            # still vanished, first vanished node appearance wins so we keep the existing entry
            return


def _changed_service(service: AutocheckEntry, compare_service: AutocheckEntry) -> bool:
    return service.comparator() != compare_service.comparator()
