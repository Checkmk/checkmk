#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Discovery of HostLabels."""
from collections.abc import Iterable, Mapping, Sequence
from typing import TypeVar

from cmk.utils.exceptions import MKGeneralException, MKTimeout, OnError
from cmk.utils.labels import DiscoveredHostLabelsStore, HostLabel
from cmk.utils.log import console
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher
from cmk.utils.type_defs import HostName, SectionName

from cmk.checkers import HostKey, PHostLabelDiscoveryPlugin, SourceType

import cmk.base.config as config
from cmk.base.agent_based.data_provider import Provider, ResolvedResult

from .utils import QualifiedDiscovery

__all__ = [
    "analyse_host_labels",
    "analyse_cluster_labels",
    "rewrite_cluster_host_labels_file",
    "discover_host_labels",
    "do_load_labels",
]


def analyse_cluster_labels(
    cluster_name: HostName,
    node_names: Sequence[HostName],
    *,
    discovered_host_labels: Mapping[HostName, Sequence[HostLabel]],
    existing_host_labels: Mapping[HostName, Sequence[HostLabel]],
    clusters_existing_host_labels: Sequence[HostLabel],
    ruleset_matcher: RulesetMatcher,
) -> tuple[QualifiedDiscovery[HostLabel], Mapping[HostName, Sequence[HostLabel]]]:

    kept_labels: dict[HostName, Sequence[HostLabel]] = {}
    for node_name in node_names:
        _node_labels, kept_node_labels = analyse_host_labels(
            node_name,
            discovered_host_labels=discovered_host_labels.get(node_name, ()),
            existing_host_labels=existing_host_labels.get(node_name, ()),
            ruleset_matcher=ruleset_matcher,
            save_labels=False,
        )
        kept_labels.update(kept_node_labels)

    cluster_labels = QualifiedDiscovery[HostLabel](
        preexisting=clusters_existing_host_labels,
        current=_merge_cluster_labels_sequence(
            nodes_labels for node in node_names if (nodes_labels := kept_labels.get(node))
        ),
        key=lambda hl: hl.label,
    )
    kept_labels[cluster_name] = list(_iter_kept_labels(cluster_labels))

    return cluster_labels, kept_labels


_TLabel = TypeVar("_TLabel")


def _merge_cluster_labels_sequence(
    all_node_labels: Iterable[Iterable[HostLabel]],
) -> Sequence[HostLabel]:
    # rigorously use HostLabels until serialization in DiscoveredHostLabelsStore and consolidate with _merge_cluster_labels...
    return list(
        _merge_cluster_labels([{l.name: l for l in labels} for labels in all_node_labels]).values()
    )


def _merge_cluster_labels(
    all_node_labels: Sequence[Mapping[str, _TLabel]]
) -> Mapping[str, _TLabel]:
    """A cluster has all its nodes labels. Last node wins."""
    return {name: label for node_labels in all_node_labels for name, label in node_labels.items()}


def rewrite_cluster_host_labels_file(
    config_cache: config.ConfigCache, nodes: Iterable[HostName]
) -> None:
    affected_clusters = {
        cluster for node_name in nodes for cluster in config_cache.clusters_of(node_name)
    }
    for cluster in affected_clusters:
        DiscoveredHostLabelsStore(cluster).save(
            _merge_cluster_labels(
                [
                    DiscoveredHostLabelsStore(node_name).load()
                    for node_name in (config_cache.nodes_of(cluster) or ())  # "or ()" just for mypy
                ]
            )
        )


def analyse_host_labels(
    host_name: HostName,
    *,
    discovered_host_labels: Sequence[HostLabel],
    existing_host_labels: Sequence[HostLabel],
    ruleset_matcher: RulesetMatcher,
    save_labels: bool,
) -> tuple[QualifiedDiscovery[HostLabel], Mapping[HostName, Sequence[HostLabel]]]:

    host_labels = QualifiedDiscovery[HostLabel](
        preexisting=existing_host_labels,
        current=discovered_host_labels,
        key=lambda hl: hl.label,
    )

    kept_labels = list(_iter_kept_labels(host_labels))
    if save_labels:
        DiscoveredHostLabelsStore(host_name).save(
            # TODO: serialization should move down the stack.
            {label.name: label.to_dict() for label in kept_labels}
        )

    if host_labels.new:  # what about vanished or changed?
        # Some check plugins like 'df' may discover services based on host labels.
        # A rule may look like:
        # [{
        #     'value': {
        #         'ignore_fs_types': ['tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660'],
        #         'never_ignore_mountpoints': ['~.*/omd/sites/[^/]+/tmp$']
        #     },
        #     'condition': {
        #         'host_labels': {
        #             'cmk/check_mk_server': 'yes'
        #         }
        #     }
        # }]
        # In the first step 'discover_host_labels' the ruleset optimizer caches the
        # result of the evaluation of these rules. Contemporary we may find new host
        # labels which are not yet taken into account by the ruleset optimizer.
        # In the next step '_discover_services' we want to discover new services
        # based on these new host labels but we only got the cached result.
        # If we found new host labels, we have to evaluate these rules again in order
        # to find new services, eg. in 'inventory_df'. Thus we have to clear these caches.
        #
        # NOTE: currently this only works if we write the host labels to disk.
        ruleset_matcher.clear_caches()

    return host_labels, {host_name: kept_labels}


def do_load_labels(host_name: HostName) -> Sequence[HostLabel]:
    raw_label_dict = DiscoveredHostLabelsStore(host_name).load()
    return [HostLabel.from_dict(name, value) for name, value in raw_label_dict.items()]


def _iter_kept_labels(host_labels: QualifiedDiscovery[HostLabel]) -> Iterable[HostLabel]:
    # TODO (mo): Clean this up, the logic is all backwards:
    # It seems we always keep the vanished ones here.
    # However: If we do not load the existing ones, no labels will be classified as 'vanished',
    # and the ones that *are* in fact vanished are dropped silently.
    yield from host_labels.vanished
    yield from host_labels.present


def discover_host_labels(
    host_name: HostName,
    host_label_plugins: Mapping[SectionName, PHostLabelDiscoveryPlugin],
    *,
    providers: Mapping[HostKey, Provider],
    on_error: OnError,
) -> Sequence[HostLabel]:

    # make names unique
    labels_by_name = {
        **_discover_host_labels_for_source_type(
            host_label_plugins,
            host_key=HostKey(host_name, SourceType.HOST),
            providers=providers,
            on_error=on_error,
        ),
        **_discover_host_labels_for_source_type(
            host_label_plugins,
            host_key=HostKey(host_name, SourceType.MANAGEMENT),
            providers=providers,
            on_error=on_error,
        ),
    }
    return list(labels_by_name.values())


def _all_parsing_results(
    host_key: HostKey,
    providers: Mapping[HostKey, Provider],
) -> Sequence[ResolvedResult]:
    try:
        resolver = providers[host_key]
    except KeyError:
        return ()

    return sorted(
        (
            res
            for psn in {
                section.parsed_section_name for section in resolver.section_plugins.values()
            }
            if (res := resolver.resolve(psn)) is not None
        ),
        key=lambda r: r.section_name,
    )


def _discover_host_labels_for_source_type(
    host_label_plugins: Mapping[SectionName, PHostLabelDiscoveryPlugin],
    *,
    host_key: HostKey,
    providers: Mapping[HostKey, Provider],
    on_error: OnError,
) -> Mapping[str, HostLabel]:

    host_labels = {}
    try:
        parsed_results = _all_parsing_results(host_key, providers)

        console.vverbose(
            "Trying host label discovery with: %s\n"
            % ", ".join(str(r.section_name) for r in parsed_results)
        )
        for section_name, section_data, _cache_info in parsed_results:

            kwargs = {"section": section_data}

            host_label_plugin = host_label_plugins[section_name]
            host_label_params = config.get_host_label_parameters(
                host_key.hostname,
                host_label_plugin,
            )
            if host_label_params is not None:
                kwargs["params"] = host_label_params

            try:
                for label in host_label_plugin.host_label_function(**kwargs):
                    console.vverbose(f"  {label.name}: {label.value} ({section_name})\n")
                    host_labels[label.name] = HostLabel(label.name, label.value, section_name)
            except (KeyboardInterrupt, MKTimeout):
                raise
            except Exception as exc:
                if on_error is OnError.RAISE:
                    raise
                if on_error is OnError.WARN:
                    console.error(f"Host label discovery of '{section_name}' failed: {exc}\n")

    except KeyboardInterrupt:
        raise MKGeneralException("Interrupted by Ctrl-C.")

    return host_labels


# snmp_info.include sets a couple of host labels for device type but should not
# overwrite device specific ones. So we put the snmp_info section first.
def _sort_sections_by_label_priority(sections):
    return sorted(sections, key=lambda s: (str(s.name) != "snmp_info", s.name))
