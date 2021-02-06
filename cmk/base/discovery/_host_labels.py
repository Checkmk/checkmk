#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (
    Dict,
    Mapping,
    Optional,
    Sequence,
)
import cmk.utils.debug
from cmk.utils.exceptions import MKGeneralException, MKTimeout
from cmk.utils.labels import DiscoveredHostLabelsStore
from cmk.utils.log import console
from cmk.utils.type_defs import (
    HostAddress,
    HostName,
    SourceType,
)
import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
import cmk.base.section as section
from cmk.base.sources.host_sections import HostKey, ParsedSectionsBroker
from cmk.base.discovered_labels import HostLabel

from .type_defs import DiscoveryParameters
from .utils import QualifiedDiscovery


def analyse_host_labels(
    *,
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    parsed_sections_broker: ParsedSectionsBroker,
    discovery_parameters: DiscoveryParameters,
) -> QualifiedDiscovery[HostLabel]:
    """Discovers host labels and services per real host or node"""

    return _analyse_host_labels(
        host_name=host_name,
        discovered_host_labels=_discover_host_labels(
            host_name=host_name,
            ipaddress=ipaddress,
            parsed_sections_broker=parsed_sections_broker,
            discovery_parameters=discovery_parameters,
        ),
        existing_host_labels=_load_existing_host_labels(
            host_name=host_name,
            discovery_parameters=discovery_parameters,
        ),
        discovery_parameters=discovery_parameters,
    )


def analyse_cluster_host_labels(
    *,
    host_config: config.HostConfig,
    ipaddress: Optional[str],
    parsed_sections_broker: ParsedSectionsBroker,
    discovery_parameters: DiscoveryParameters,
) -> QualifiedDiscovery[HostLabel]:
    if not host_config.nodes:
        return QualifiedDiscovery.empty()

    nodes_host_labels: Dict[str, HostLabel] = {}
    config_cache = config.get_config_cache()

    for node in host_config.nodes:
        node_config = config_cache.get_host_config(node)
        node_ipaddress = ip_lookup.lookup_ip_address(node_config,
                                                     family=node_config.default_address_family)

        node_result = analyse_host_labels(
            host_name=node,
            ipaddress=node_ipaddress,
            parsed_sections_broker=parsed_sections_broker,
            discovery_parameters=discovery_parameters,
        )

        # keep the latest for every label.name
        nodes_host_labels.update({
            # TODO (mo): According to unit tests, this is what was done prior to refactoring.
            # Im not sure this is desired. If it is, it should be explained.
            **{l.name: l for l in node_result.vanished},
            **{l.name: l for l in node_result.present},
        })

    return _analyse_host_labels(
        host_name=host_config.hostname,
        discovered_host_labels=list(nodes_host_labels.values()),
        existing_host_labels=_load_existing_host_labels(
            host_name=host_config.hostname,
            discovery_parameters=discovery_parameters,
        ),
        discovery_parameters=discovery_parameters,
    )


def _analyse_host_labels(
    *,
    host_name: HostName,
    discovered_host_labels: Sequence[HostLabel],
    existing_host_labels: Sequence[HostLabel],
    discovery_parameters: DiscoveryParameters,
) -> QualifiedDiscovery[HostLabel]:

    section.section_step("Analyse discovered host labels")

    host_labels = QualifiedDiscovery(
        preexisting=existing_host_labels,
        current=discovered_host_labels,
        key=lambda hl: hl.label,
    )

    if discovery_parameters.save_labels:
        DiscoveredHostLabelsStore(host_name).save({
            # TODO (mo): Im not sure this is desired. If it is, it should be explained.
            **{l.name: l.to_dict() for l in host_labels.vanished},
            **{l.name: l.to_dict() for l in host_labels.present},
        })

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


def _load_existing_host_labels(
    *,
    host_name: HostName,
    discovery_parameters: DiscoveryParameters,
) -> Sequence[HostLabel]:
    # Take over old items if -I is selected
    if not discovery_parameters.load_labels:
        return []

    raw_label_dict = DiscoveredHostLabelsStore(host_name).load()
    return [HostLabel.from_dict(name, value) for name, value in raw_label_dict.items()]


def _discover_host_labels(
    *,
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    parsed_sections_broker: ParsedSectionsBroker,
    discovery_parameters: DiscoveryParameters,
) -> Sequence[HostLabel]:

    section.section_step("Discover host labels of section plugins")

    # make names unique
    labels_by_name = {
        **_discover_host_labels_for_source_type(
            host_key=HostKey(host_name, ipaddress, SourceType.HOST),
            parsed_sections_broker=parsed_sections_broker,
            discovery_parameters=discovery_parameters,
        ),
        **_discover_host_labels_for_source_type(
            host_key=HostKey(host_name, ipaddress, SourceType.MANAGEMENT),
            parsed_sections_broker=parsed_sections_broker,
            discovery_parameters=discovery_parameters,
        ),
    }
    return list(labels_by_name.values())


def _discover_host_labels_for_source_type(
    *,
    host_key: HostKey,
    parsed_sections_broker: ParsedSectionsBroker,
    discovery_parameters: DiscoveryParameters,
) -> Mapping[str, HostLabel]:

    try:
        host_data = parsed_sections_broker[host_key]
    except KeyError:
        return {}

    host_labels = {}
    try:
        # We do *not* process all available raw sections. Instead we see which *parsed*
        # sections would result from them, and then process those.
        parse_sections = {
            agent_based_register.get_section_plugin(rs).parsed_section_name
            for rs in host_data.sections
        }
        applicable_sections = parsed_sections_broker.determine_applicable_sections(
            parse_sections,
            host_key.source_type,
        )

        console.vverbose("Trying host label discovery with: %s\n" %
                         ", ".join(str(s.name) for s in applicable_sections))
        for section_plugin in _sort_sections_by_label_priority(applicable_sections):

            kwargs = {
                'section': parsed_sections_broker.get_parsed_section(
                    host_key, section_plugin.parsed_section_name),
            }

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
                if cmk.utils.debug.enabled() or discovery_parameters.on_error == "raise":
                    raise
                if discovery_parameters.on_error == "warn":
                    console.error("Host label discovery of '%s' failed: %s\n" %
                                  (section_plugin.name, exc))

    except KeyboardInterrupt:
        raise MKGeneralException("Interrupted by Ctrl-C.")

    return host_labels


# snmp_info.include sets a couple of host labels for device type but should not
# overwrite device specific ones. So we put the snmp_info section first.
def _sort_sections_by_label_priority(sections):
    return sorted(sections, key=lambda s: (str(s.name) != "snmp_info", s.name))
