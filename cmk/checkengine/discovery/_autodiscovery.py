#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import dataclasses
import itertools
import time
from collections.abc import Callable, Container, Iterable, Mapping, Sequence
from typing import assert_never, Generic, Literal, TypeVar

import cmk.ccc.debug
from cmk.ccc.exceptions import MKGeneralException, MKTimeout, OnError
from cmk.ccc.hostaddress import HostName

from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.labels import DiscoveredHostLabelsStore, HostLabel, merge_cluster_labels
from cmk.utils.log import console, section
from cmk.utils.paths import omd_root
from cmk.utils.sectionname import SectionMap, SectionName
from cmk.utils.servicename import ServiceName

from cmk.checkengine.fetcher import FetcherFunction, HostKey
from cmk.checkengine.parser import group_by_host, ParserFunction
from cmk.checkengine.plugins import AutocheckEntry, CheckPluginName, DiscoveryPlugin, ServiceID
from cmk.checkengine.sectionparser import (
    make_providers,
    Provider,
    SectionPlugin,
    store_piggybacked_sections,
)
from cmk.checkengine.summarize import SummarizerFunction

from ._autochecks import (
    AutochecksConfig,
    AutocheckServiceWithNodes,
    AutochecksStore,
    merge_cluster_autochecks,
    set_autochecks_of_cluster,
    set_autochecks_of_real_hosts,
)
from ._filters import RediscoveryParameters
from ._filters import ServiceFilters as _ServiceFilters
from ._host_labels import discover_host_labels, HostLabelPlugin
from ._services import analyse_services, discover_services, find_plugins
from ._utils import DiscoveredItem, DiscoverySettings, QualifiedDiscovery

__all__ = ["get_host_services_by_host_name", "discovery_by_host"]


@dataclasses.dataclass
class TransitionCounter:
    new: int = 0
    changed: int = 0
    removed: int = 0
    kept: int = 0

    @property
    def total(self) -> int:
        return self.new + self.changed + self.removed + self.kept

    @property
    def has_changes(self) -> bool:
        return self.new > 0 or self.changed > 0 or self.removed > 0

    def __iadd__(self, other: TransitionCounter) -> TransitionCounter:
        self.new += other.new
        self.changed += other.changed
        self.removed += other.removed
        self.kept += other.kept
        return self

    def __add__(self, other: TransitionCounter) -> TransitionCounter:
        return TransitionCounter(
            new=self.new + other.new,
            changed=self.changed + other.changed,
            removed=self.removed + other.removed,
            kept=self.kept + other.kept,
        )


@dataclasses.dataclass
class DiscoveryReport:
    services: TransitionCounter = dataclasses.field(default_factory=TransitionCounter)
    host_labels: TransitionCounter = dataclasses.field(default_factory=TransitionCounter)
    clustered_new: int = 0
    clustered_old: int = 0
    clustered_vanished: int = 0
    clustered_ignored: int = 0

    # None  -> No error occurred
    # ""    -> Not monitored (disabled host)
    # "..." -> An error message about the failed discovery
    error_text: str | None = None

    # An optional text to describe the services changed by the operation
    diff_text: str | None = None


_BasicTransition = Literal["changed", "unchanged", "new", "vanished"]
_Transition = (
    _BasicTransition
    | Literal[
        "ignored", "clustered_old", "clustered_new", "clustered_vanished", "clustered_ignored"
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
# param servic_filter: if a filter is set, it controls whether items are touched by the discovery.
#                       if it returns False for a new item it will not be added, if it returns
#                       False for a vanished item, that item is kept
def automation_discovery(
    host_name: HostName,
    *,
    # in the bulk discovery case, we might be dealing with a cluster
    is_cluster: bool,
    cluster_nodes: Sequence[HostName],
    active_hosts: Container[HostName],
    clear_ruleset_matcher_caches: Callable[[], object],
    parser: ParserFunction,
    fetcher: FetcherFunction,
    summarizer: SummarizerFunction,
    section_plugins: SectionMap[SectionPlugin],
    host_label_plugins: SectionMap[HostLabelPlugin],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    autochecks_config: AutochecksConfig,
    settings: DiscoverySettings,
    keep_clustered_vanished_services: bool,
    service_filters: _ServiceFilters | None,
    enforced_services: Container[ServiceID],
    on_error: OnError,
    section_error_handling: Callable[[SectionName, Sequence[object]], str],
) -> DiscoveryReport:
    console.verbose(f"  Doing discovery with '{settings!r}'...")
    results = {
        host_name: DiscoveryReport(),
        **{node: DiscoveryReport() for node in cluster_nodes},
    }
    if host_name not in active_hosts:
        results[host_name].error_text = ""
        return results[host_name]

    service_changes_requested = (
        settings.add_new_services
        or settings.remove_vanished_services
        or settings.update_changed_service_labels
        or settings.update_changed_service_parameters
    )

    try:
        fetched = fetcher(host_name, ip_address=None)
        host_sections = parser((f[0], f[1]) for f in fetched)
        if failed_sources_results := [r for r in summarizer(host_sections) if r.state != 0]:
            return DiscoveryReport(error_text=", ".join(r.summary for r in failed_sources_results))

        host_sections_by_host = group_by_host(
            ((HostKey(s.hostname, s.source_type), r.ok) for s, r in host_sections if r.is_ok()),
            console.debug,
        )
        store_piggybacked_sections(host_sections_by_host, omd_root)
        providers = make_providers(
            host_sections_by_host,
            section_plugins,
            error_handling=section_error_handling,
        )

        if settings.update_host_labels and not is_cluster:
            host_labels = QualifiedDiscovery[HostLabel](
                preexisting=DiscoveredHostLabelsStore(host_name).load(),
                current=discover_host_labels(
                    host_name,
                    host_label_plugins,
                    providers=providers,
                    on_error=on_error,
                ),
            )
            DiscoveredHostLabelsStore(host_name).save(host_labels.present)
            if not service_changes_requested:
                results[host_name].diff_text = _make_diff(
                    host_labels.vanished, host_labels.new, (), ()
                )
                return results[host_name]
        else:
            unchanged_labels = (
                merge_cluster_labels(
                    [DiscoveredHostLabelsStore(node).load() for node in cluster_nodes]
                )
                if is_cluster
                else DiscoveredHostLabelsStore(host_name).load()
            )
            host_labels = QualifiedDiscovery(
                preexisting=unchanged_labels,
                current=unchanged_labels,
            )

        if host_labels.new or host_labels.vanished or host_labels.changed:
            # Rulesets for service discovery can match based on the hosts labels.
            clear_ruleset_matcher_caches()

        # Compute current state of new and existing checks
        services_by_host_name = get_host_services_by_host_name(
            host_name,
            existing_services=(
                {n: AutochecksStore(n).read() for n in cluster_nodes}
                if is_cluster
                else {host_name: AutochecksStore(host_name).read()}
            ),
            discovered_services=discovery_by_host(
                cluster_nodes if is_cluster else (host_name,),
                providers,
                plugins,
                on_error,
            ),
            is_cluster=is_cluster,
            cluster_nodes=cluster_nodes,
            autochecks_config=autochecks_config,
            enforced_services=enforced_services,
        )

        existing_services_by_host = {
            h: {
                x.service.older.id(): x
                for x in itertools.chain(
                    services.get("changed", []),
                    services.get("unchanged", []),
                )
            }
            for h, services in services_by_host_name.items()
        }

        # Create new list of checks
        final_services_by_host = {
            h: _get_post_discovery_autocheck_services(
                h,
                s,
                service_filters or _ServiceFilters.accept_all(),
                results[h],
                autochecks_config.service_description,
                settings,
                keep_clustered_vanished_services,
            )
            for h, s in services_by_host_name.items()
        }
        new_services_by_host = {h: list(s.values()) for h, s in final_services_by_host.items()}
        if is_cluster:
            set_autochecks_of_cluster(
                cluster_nodes,
                host_name,
                new_services_by_host,
                autochecks_config.effective_host,
            )
        else:
            set_autochecks_of_real_hosts(host_name, new_services_by_host[host_name])

        results[host_name].host_labels = TransitionCounter(
            new=len(host_labels.new),
            changed=len(host_labels.changed),
            removed=len(host_labels.vanished),
            kept=len(host_labels.unchanged),
        )
        results[host_name].diff_text = _make_diff(
            host_labels.vanished,
            host_labels.new,
            (
                x.service
                for x in existing_services_by_host[host_name].values()
                if x.service.newer.id() not in final_services_by_host[host_name]
            ),
            (
                x.service
                for x in final_services_by_host[host_name].values()
                if x.service.newer.id() not in existing_services_by_host[host_name]
            ),
        )

    except MKTimeout:
        raise  # let general timeout through

    except Exception as e:
        if cmk.ccc.debug.enabled():
            raise
        results[host_name].error_text = str(e)

    # For now, we only return the result for the host itself
    return results[host_name]


def _get_post_discovery_autocheck_services(
    host_name: HostName,
    services: ServicesByTransition,
    service_filters: _ServiceFilters,
    result: DiscoveryReport,
    get_service_description: Callable[[HostName, AutocheckEntry], ServiceName],
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
        match check_transition:
            case "new":
                if settings.add_new_services:
                    new = {
                        s.service.newer.id(): s
                        for s in discovered_services_with_nodes
                        if service_filters.new(get_service_description(host_name, s.service.newer))
                    }
                    result.services.new += len(new)
                    post_discovery_services.update(new)

            case "unchanged" | "ignored":
                # keep currently existing valid services in any case
                post_discovery_services.update(
                    (s.service.newer.id(), s) for s in discovered_services_with_nodes
                )
                result.services.kept += len(discovered_services_with_nodes)

            case "changed":
                for entry in discovered_services_with_nodes:
                    service = entry.service
                    assert service.previous is not None and service.new is not None
                    new_entry = AutocheckServiceWithNodes(
                        service=DiscoveredItem[AutocheckEntry](
                            new=AutocheckEntry(
                                check_plugin_name=service.newer.check_plugin_name,
                                item=service.newer.item,
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
                    post_discovery_services[service.newer.id()] = new_entry
                    if new_entry.service.new != new_entry.service.previous:
                        result.services.changed += 1
                    else:
                        result.services.kept += 1

            case "vanished":
                # keep item, if we are currently only looking for new services
                # otherwise fix it: remove ignored and non-longer existing services
                for entry in discovered_services_with_nodes:
                    if settings.remove_vanished_services and service_filters.vanished(
                        get_service_description(host_name, entry.service.newer)
                    ):
                        result.services.removed += 1
                    else:
                        post_discovery_services[entry.service.newer.id()] = entry

                        result.services.kept += 1

            case _:
                if check_transition != "clustered_vanished" or keep_clustered_vanished_services:
                    # Silently keep clustered services
                    post_discovery_services.update(
                        (s.service.newer.id(), s) for s in discovered_services_with_nodes
                    )
                match check_transition:
                    case "clustered_new":
                        result.clustered_new += len(discovered_services_with_nodes)
                    case "clustered_old":
                        result.clustered_old += len(discovered_services_with_nodes)
                    case "clustered_vanished":
                        result.clustered_vanished += len(discovered_services_with_nodes)
                    case "clustered_ignored":
                        result.clustered_ignored += len(discovered_services_with_nodes)
                    case _:
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
                        f"Removed service: Check plug-in '{s.newer.check_plugin_name}'."
                        if s.newer.item is None
                        else f"Removed service: Check plug-in '{s.newer.check_plugin_name}' / item '{s.newer.item}'."
                    )
                    for s in services_vanished
                ),
                *(
                    (
                        f"Added service: Check plug-in '{s.newer.check_plugin_name}'."
                        if s.newer.item is None
                        else f"Added service: Check plug-in '{s.newer.check_plugin_name}' / item '{s.newer.item}'."
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
    cluster_nodes: Sequence[HostName],
    active_hosts: Container[HostName],
    clear_ruleset_matcher_caches: Callable[[], object],
    fetcher: FetcherFunction,
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    section_plugins: SectionMap[SectionPlugin],
    section_error_handling: Callable[[SectionName, Sequence[object]], str],
    host_label_plugins: SectionMap[HostLabelPlugin],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    autochecks_config: AutochecksConfig,
    schedule_discovery_check: Callable[[HostName], object],
    rediscovery_parameters: RediscoveryParameters,
    invalidate_host_config: Callable[[], object],
    reference_time: float,
    oldest_queued: float,
    enforced_services: Container[ServiceID],
    on_error: OnError,
) -> tuple[DiscoveryReport | None, bool]:
    reason = _may_rediscover(
        rediscovery_parameters=rediscovery_parameters,
        reference_time=reference_time,
        oldest_queued=oldest_queued,
    )
    if reason:
        console.verbose(f"  skipped: {reason}")
        return None, False

    result = automation_discovery(
        host_name,
        is_cluster=False,
        cluster_nodes=cluster_nodes,
        active_hosts=active_hosts,
        clear_ruleset_matcher_caches=clear_ruleset_matcher_caches,
        parser=parser,
        fetcher=fetcher,
        summarizer=summarizer,
        section_plugins=section_plugins,
        section_error_handling=section_error_handling,
        host_label_plugins=host_label_plugins,
        plugins=plugins,
        autochecks_config=autochecks_config,
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
        console.verbose(f"  failed: {result.error_text or 'host is offline'}")
        return None, False

    something_changed = (
        result.services.has_changes
        or result.host_labels.has_changes
        or result.clustered_new != 0
        or result.clustered_vanished != 0
    )

    if not something_changed:
        console.verbose("  nothing changed.")
        activation_required = False
    else:
        console.verbose_no_lf(
            f"{result.services.total} services ({result.services.new} added, {result.services.changed} changed, "
            f"{result.services.removed} removed, {result.services.kept} kept, {result.clustered_new} clustered new, "
            f"{result.clustered_vanished}  clustered vanished) "
            f"and {result.host_labels.total} host labels ({result.host_labels.new} added, {result.host_labels.changed} changed, "
            f"{result.host_labels.removed} removed, {result.host_labels.kept} kept). "
        )

        # Note: Even if the actual mark-for-discovery flag may have been created by a cluster host,
        #       the activation decision is based on the discovery configuration of the node
        activation_required = bool(rediscovery_parameters["activation"])

        # Enforce base code creating a new host config object after this change
        invalidate_host_config()

        # Now ensure that the discovery service is updated right after the changes
        schedule_discovery_check(host_name)

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
def get_host_services_by_host_name(
    host_name: HostName,
    *,
    existing_services: Mapping[HostName, Sequence[AutocheckEntry]],
    discovered_services: Mapping[HostName, Sequence[AutocheckEntry]],
    is_cluster: bool,
    cluster_nodes: Iterable[HostName],
    autochecks_config: AutochecksConfig,
    enforced_services: Container[ServiceID],
) -> dict[HostName, ServicesByTransition]:
    services_by_host_name: dict[HostName, ServicesTable[_Transition]]
    if is_cluster:
        services_by_host_name = {
            **_get_cluster_services(
                host_name,
                existing_services=existing_services,
                discovered_services=discovered_services,
                cluster_nodes=cluster_nodes,
                autochecks_config=autochecks_config,
            )
        }
    else:
        services_by_host_name = {
            host_name: {
                **make_table(
                    host_name,
                    analyse_services(
                        existing_services=existing_services[host_name],
                        discovered_services=discovered_services[host_name],
                        run_plugin_names=EVERYTHING,
                        forget_existing=False,
                        keep_vanished=False,
                    ),
                    autochecks_config,
                )
            }
        }

    # remove the ones shadowed by enforced services
    return {
        h: _group_by_transition({k: v for k, v in s.items() if k not in enforced_services})
        for h, s in services_by_host_name.items()
    }


def discovery_by_host(  # should go to a different file, I think.
    host_names: Sequence[HostName],
    providers: Mapping[HostKey, Provider],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    on_error: OnError,
) -> Mapping[HostName, Sequence[AutocheckEntry]]:
    candidates = find_plugins(
        providers,
        [(plugin_name, plugin.sections) for plugin_name, plugin in plugins.items()],
    )

    section.section_step("Executing discovery plugins (%d)" % len(candidates))
    console.debug(f"  Trying discovery with: {', '.join(str(n) for n in candidates)}")

    try:
        discovered_services = {
            host_name: discover_services(
                host_name, candidates, providers=providers, plugins=plugins, on_error=on_error
            )
            for host_name in host_names
        }
    except KeyboardInterrupt:
        raise MKGeneralException("Interrupted by Ctrl-C.")

    return discovered_services


def make_table(
    host_name: HostName,
    entries: QualifiedDiscovery[AutocheckEntry],
    autochecks_config: AutochecksConfig,
) -> ServicesTable[_Transition]:
    return {
        entry.newer.id(): ServicesTableEntry(
            transition=_node_service_source(
                host_name,
                entry.newer,
                ignore_service=autochecks_config.ignore_service,
                ignore_plugin=autochecks_config.ignore_plugin,
                check_source=service_transition,
                cluster_name=autochecks_config.effective_host(host_name, entry.newer),
            ),
            autocheck=entry,
            hosts=[host_name],
        )
        for service_transition, entry in entries.chain_with_transition()
    }


def _node_service_source(
    host_name: HostName,
    entry: AutocheckEntry,
    *,
    ignore_service: Callable[[HostName, AutocheckEntry], bool],
    ignore_plugin: Callable[[HostName, CheckPluginName], bool],
    check_source: _BasicTransition,
    cluster_name: HostName,
) -> _Transition:
    if host_name == cluster_name:
        return (
            "ignored"
            if ignore_plugin(host_name, entry.check_plugin_name) or ignore_service(host_name, entry)
            else check_source
        )

    # TODO: this does not make much sense. If the service is clustered, but ignored _on that cluster_, it should be shown there.
    if ignore_service(cluster_name, entry) or ignore_plugin(cluster_name, entry.check_plugin_name):
        return "ignored"

    if check_source == "vanished":
        return "clustered_vanished"
    if check_source in ("changed", "unchanged"):
        return "clustered_old"
    return "clustered_new"


def _make_cluster_table(
    entries: QualifiedDiscovery[AutocheckEntry],
    node_tables: Mapping[HostName, ServicesTable[_Transition]],
    is_ignored_on_cluster: Callable[[AutocheckEntry], bool],
) -> ServicesTable[_Transition]:
    return {
        (sid := entry.newer.id()): ServicesTableEntry(
            transition="ignored" if is_ignored_on_cluster(entry.newer) else service_transition,
            autocheck=entry,
            hosts=[
                hn
                for hn, entries in node_tables.items()
                if sid in entries and entries[sid].autocheck.new is not None
            ],
        )
        for service_transition, entry in entries.chain_with_transition()
    }


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
    existing_services: Mapping[HostName, Sequence[AutocheckEntry]],
    discovered_services: Mapping[HostName, Sequence[AutocheckEntry]],
    autochecks_config: AutochecksConfig,
) -> dict[HostName, ServicesTable[_Transition]]:
    # should/can we move these up the stack?
    def is_ignored(hn: HostName, entry: AutocheckEntry) -> bool:
        if autochecks_config.ignore_plugin(hn, entry.check_plugin_name):
            return True
        return autochecks_config.ignore_service(hn, entry)

    def appears_on_cluster(node_name: HostName, entry: AutocheckEntry) -> bool:
        return (
            not is_ignored(node_name, entry)
            and autochecks_config.effective_host(node_name, entry) == host_name
        )

    nodes_discovery_results = {
        node: analyse_services(
            existing_services=existing_services[node],
            discovered_services=discovered_services[node],
            run_plugin_names=EVERYTHING,
            forget_existing=False,
            keep_vanished=False,
        )
        for node in cluster_nodes
    }
    node_tables = {
        hn: make_table(hn, entries, autochecks_config)
        for hn, entries in nodes_discovery_results.items()
    }
    clusters_discovery_result = QualifiedDiscovery(
        preexisting=merge_cluster_autochecks(
            {hn: q.preexisting for hn, q in nodes_discovery_results.items()},
            appears_on_cluster,
        ),
        current=merge_cluster_autochecks(
            {hn: q.current for hn, q in nodes_discovery_results.items()},
            appears_on_cluster,
        ),
    )

    return {
        host_name: _make_cluster_table(
            clusters_discovery_result,
            node_tables,
            is_ignored_on_cluster=lambda entry: is_ignored(host_name, entry),
        ),
        **node_tables,
    }
