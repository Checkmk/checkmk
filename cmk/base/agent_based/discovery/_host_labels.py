#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Discovery of HostLabels

This module exposes three functions:
 * analyse_node_labels
 * analyse_cluster_labels
 * analyse_host_labels (dispatching to one of the above based on host_config.is_cluster)

"""
from typing import Dict, Mapping, Sequence

from cmk.utils.exceptions import MKGeneralException, MKTimeout, OnError
from cmk.utils.labels import DiscoveredHostLabelsStore
from cmk.utils.log import console
from cmk.utils.type_defs import HostKey, HostName

import cmk.base.config as config
from cmk.base.agent_based.data_provider import ParsedSectionsBroker
from cmk.base.discovered_labels import HostLabel

from .utils import QualifiedDiscovery


def analyse_host_labels(
    *,
    host_config: config.HostConfig,
    load_labels: bool,
    save_labels: bool,
    parsed_sections_broker: ParsedSectionsBroker,
    on_error: OnError,
) -> QualifiedDiscovery[HostLabel]:
    return (
        analyse_cluster_labels(
            host_config=host_config,
            parsed_sections_broker=parsed_sections_broker,
            load_labels=load_labels,
            save_labels=save_labels,
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
) -> QualifiedDiscovery[HostLabel]:
    """Discovers and processes host labels per real host or node

    Side effects:
     * may write to disk
     * may reset ruleset optimizer

    If specified in the discovery_parameters, the host labels after
    the discovery are persisted on disk.

    Some plugins discover services based on host labels, so the ruleset
    optimizer caches have to be cleared if new host labels are found.
    """
    return _analyse_host_labels(
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


def analyse_cluster_labels(
    *,
    host_config: config.HostConfig,
    parsed_sections_broker: ParsedSectionsBroker,
    load_labels: bool,
    save_labels: bool,
    on_error: OnError,
) -> QualifiedDiscovery[HostLabel]:
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
        return QualifiedDiscovery.empty()

    nodes_host_labels: Dict[str, HostLabel] = {}
    config_cache = config.get_config_cache()

    for node in host_config.nodes:
        node_config = config_cache.get_host_config(node)

        node_result = analyse_node_labels(
            host_key=node_config.host_key,
            host_key_mgmt=node_config.host_key_mgmt,
            parsed_sections_broker=parsed_sections_broker,
            load_labels=load_labels,
            save_labels=save_labels,
            on_error=on_error,
        )

        # keep the latest for every label.name
        nodes_host_labels.update(
            {
                # TODO (mo): According to unit tests, this is what was done prior to refactoring.
                # I'm not sure this is desired. If it is, it should be explained.
                # Whenever we do not load the host labels, vanished will be empty.
                **{l.name: l for l in node_result.vanished},
                **{l.name: l for l in node_result.present},
            }
        )

    return _analyse_host_labels(
        host_name=host_config.hostname,
        discovered_host_labels=list(nodes_host_labels.values()),
        existing_host_labels=_load_existing_host_labels(host_config.hostname)
        if load_labels
        else (),
        save_labels=save_labels,
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

    if save_labels:
        DiscoveredHostLabelsStore(host_name).save(
            {
                # TODO (mo): I'm not sure this is desired. If it is, it should be explained.
                # Whenever we do not load the host labels, vanished will be empty.
                **{l.name: l.to_dict() for l in host_labels.vanished},
                **{l.name: l.to_dict() for l in host_labels.present},
            }
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
