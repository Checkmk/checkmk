#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Discovery of HostLabels

This module exposes three functions:
 * analyse_node_labels
 * analyse_cluster_labels
 * analyse_host_labels (dispatching to one of the above based on host_config.is_cluster)

"""
from typing import Dict, Iterable, Mapping, Sequence, TypeVar

from cmk.utils.exceptions import MKGeneralException, MKTimeout, OnError
from cmk.utils.labels import DiscoveredHostLabelsStore
from cmk.utils.log import console
from cmk.utils.type_defs import HostKey, HostName

import cmk.base.config as config
from cmk.base.agent_based.data_provider import ParsedSectionsBroker
from cmk.base.discovered_labels import HostLabel, HostLabelValueDict

from .utils import QualifiedDiscovery


def analyse_host_labels(
    *,
    host_config: config.HostConfig,
    load_labels: bool,
    save_labels: bool,
    parsed_sections_broker: ParsedSectionsBroker,
    on_error: OnError,
) -> tuple[QualifiedDiscovery[HostLabel], Mapping[HostName, Mapping[str, HostLabelValueDict]]]:
    return (
        analyse_cluster_labels(
            host_config=host_config,
            parsed_sections_broker=parsed_sections_broker,
            load_labels=load_labels,
            on_error=on_error,
        )
        if host_config.is_cluster
        else analyse_node_labels(
            host_key=host_config.host_key,
            host_key_mgmt=host_config.host_key_mgmt,
            parsed_sections_broker=parsed_sections_broker,
            load_labels=load_labels,
            save_labels=save_labels,
            on_error=on_error,
        )
    )


def analyse_node_labels(
    *,
    host_key: HostKey,
    host_key_mgmt: HostKey,
    parsed_sections_broker: ParsedSectionsBroker,
    load_labels: bool,
    save_labels: bool,
    on_error: OnError,
) -> tuple[QualifiedDiscovery[HostLabel], Mapping[HostName, Mapping[str, HostLabelValueDict]]]:
    """Discovers and processes host labels per real host or node

    Side effects:
     * may write to disk
     * may reset ruleset optimizer

    If specified in the discovery_parameters, the host labels after
    the discovery are persisted on disk.

    Some plugins discover services based on host labels, so the ruleset
    optimizer caches have to be cleared if new host labels are found.
    """
    host_labels = _analyse_host_labels(
        host_name=host_key.hostname,
        discovered_host_labels=_discover_host_labels(
            host_key=host_key,
            host_key_mgmt=host_key_mgmt,
            parsed_sections_broker=parsed_sections_broker,
            on_error=on_error,
        ),
        existing_host_labels=_load_existing_host_labels(host_key.hostname) if load_labels else (),
        save_labels=save_labels,
    )

    present_labels_dict = {l.name: l.to_dict() for l in _iter_kept_labels(host_labels)}

    if save_labels:
        DiscoveredHostLabelsStore(host_key.hostname).save(present_labels_dict)

    return host_labels, {host_key.hostname: present_labels_dict}


def analyse_cluster_labels(
    *,
    host_config: config.HostConfig,
    parsed_sections_broker: ParsedSectionsBroker,
    load_labels: bool,
    on_error: OnError,
) -> tuple[QualifiedDiscovery[HostLabel], Mapping[HostName, Mapping[str, HostLabelValueDict]]]:
    """Discovers and processes host labels per cluster host

    Side effects:
     * may write to disk
     * may reset ruleset optimizer

    If specified in the discovery_parameters, the host labels after
    the discovery are persisted on disk.

    Some plugins discover services based on host labels, so the ruleset
    optimizer caches have to be cleared if new host labels are found.
    """
    if not host_config.nodes:
        return QualifiedDiscovery.empty(), {}

    labels_by_host: Dict[HostName, Mapping[str, HostLabelValueDict]] = {}
    discovered_by_node: list[Mapping[str, HostLabel]] = []
    config_cache = config.get_config_cache()

    for node in host_config.nodes:
        node_config = config_cache.get_host_config(node)

        node_result, labels_by_node = analyse_node_labels(
            host_key=node_config.host_key,
            host_key_mgmt=node_config.host_key_mgmt,
            parsed_sections_broker=parsed_sections_broker,
            load_labels=load_labels,
            save_labels=False,
            on_error=on_error,
        )
        discovered_by_node.append({l.name: l for l in _iter_kept_labels(node_result)})

        labels_by_host.update(labels_by_node)

    cluster_result = _analyse_host_labels(
        host_name=host_config.hostname,
        discovered_host_labels=list(_merge_cluster_labels(discovered_by_node).values()),
        existing_host_labels=_load_existing_host_labels(host_config.hostname)
        if load_labels
        else (),
        save_labels=False,
    )
    return cluster_result, {
        **labels_by_host,
        host_config.hostname: {l.name: l.to_dict() for l in _iter_kept_labels(cluster_result)},
    }


_TLabel = TypeVar("_TLabel")


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


def _analyse_host_labels(
    *,
    host_name: HostName,
    discovered_host_labels: Sequence[HostLabel],
    existing_host_labels: Sequence[HostLabel],
    save_labels: bool,
) -> QualifiedDiscovery[HostLabel]:

    host_labels = QualifiedDiscovery(
        preexisting=existing_host_labels,
        current=discovered_host_labels,
        key=lambda hl: hl.label,
    )

    if host_labels.new:
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
        # In the first step '_discover_host_labels' the ruleset optimizer caches the
        # result of the evaluation of these rules. Contemporary we may find new host
        # labels which are not yet taken into account by the ruleset optimizer.
        # In the next step '_discover_services' we want to discover new services
        # based on these new host labels but we only got the cached result.
        # If we found new host labels, we have to evaluate these rules again in order
        # to find new services, eg. in 'inventory_df'. Thus we have to clear these caches.
        config.get_config_cache().ruleset_matcher.ruleset_optimizer.clear_caches()

    return host_labels


def _load_existing_host_labels(host_name: HostName) -> Sequence[HostLabel]:
    raw_label_dict = DiscoveredHostLabelsStore(host_name).load()
    return [HostLabel.from_dict(name, value) for name, value in raw_label_dict.items()]


def _iter_kept_labels(host_labels: QualifiedDiscovery[HostLabel]) -> Iterable[HostLabel]:
    yield from host_labels.present


def _discover_host_labels(
    *,
    host_key: HostKey,
    host_key_mgmt: HostKey,
    parsed_sections_broker: ParsedSectionsBroker,
    on_error: OnError,
) -> Sequence[HostLabel]:

    # make names unique
    labels_by_name = {
        **_discover_host_labels_for_source_type(
            host_key=host_key,
            parsed_sections_broker=parsed_sections_broker,
            on_error=on_error,
        ),
        **_discover_host_labels_for_source_type(
            host_key=host_key_mgmt,
            parsed_sections_broker=parsed_sections_broker,
            on_error=on_error,
        ),
    }
    return list(labels_by_name.values())


def _discover_host_labels_for_source_type(
    *,
    host_key: HostKey,
    parsed_sections_broker: ParsedSectionsBroker,
    on_error: OnError,
) -> Mapping[str, HostLabel]:

    host_labels = {}
    try:
        parsed_results = parsed_sections_broker.all_parsing_results(host_key)

        console.vverbose(
            "Trying host label discovery with: %s\n"
            % ", ".join(str(r.section.name) for r in parsed_results)
        )
        for (section_data, _cache_info), section_plugin in parsed_results:

            kwargs = {"section": section_data}

            host_label_params = config.get_host_label_parameters(host_key.hostname, section_plugin)
            if host_label_params is not None:
                kwargs["params"] = host_label_params

            try:
                for label in section_plugin.host_label_function(**kwargs):
                    console.vverbose(f"  {label.name}: {label.value} ({section_plugin.name})\n")
                    host_labels[label.name] = HostLabel(
                        label.name,
                        label.value,
                        section_plugin.name,
                    )
            except (KeyboardInterrupt, MKTimeout):
                raise
            except Exception as exc:
                if on_error is OnError.RAISE:
                    raise
                if on_error is OnError.WARN:
                    console.error(
                        f"Host label discovery of '{section_plugin.name}' failed: {exc}\n"
                    )

    except KeyboardInterrupt:
        raise MKGeneralException("Interrupted by Ctrl-C.")

    return host_labels


# snmp_info.include sets a couple of host labels for device type but should not
# overwrite device specific ones. So we put the snmp_info section first.
def _sort_sections_by_label_priority(sections):
    return sorted(sections, key=lambda s: (str(s.name) != "snmp_info", s.name))
