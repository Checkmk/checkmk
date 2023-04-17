#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Discovery of HostLabels."""
from collections.abc import Mapping, Sequence

from cmk.utils.exceptions import MKGeneralException, MKTimeout, OnError
from cmk.utils.labels import DiscoveredHostLabelsStore, HostLabel
from cmk.utils.log import console
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher
from cmk.utils.type_defs import HostName, SectionName

from cmk.checkers import HostKey, HostLabelDiscoveryPlugin, SourceType
from cmk.checkers.sectionparser import Provider, ResolvedResult

from .utils import QualifiedDiscovery

__all__ = [
    "analyse_host_labels",
    "discover_cluster_labels",
    "discover_host_labels",
    "do_load_labels",
    "do_save_labels",
]


def discover_cluster_labels(
    nodes: Sequence[HostName],
    host_label_plugins: Mapping[SectionName, HostLabelDiscoveryPlugin],
    *,
    providers: Mapping[HostKey, Provider],
    load_labels: bool,
    save_labels: bool,
    on_error: OnError,
) -> Sequence[HostLabel]:
    nodes_host_labels: dict[str, HostLabel] = {}
    for node in nodes:
        node_labels = QualifiedDiscovery[HostLabel](
            preexisting=do_load_labels(node) if load_labels else (),
            current=discover_host_labels(
                node, host_label_plugins, providers=providers, on_error=on_error
            ),
            key=lambda hl: hl.label,
        )
        if save_labels:
            do_save_labels(node, node_labels)

        # keep the latest for every label.name
        nodes_host_labels.update(
            {
                # TODO (mo): According to unit tests, this is what was done prior to refactoring.
                # I'm not sure this is desired. If it is, it should be explained.
                # Whenever we do not load the host labels, vanished will be empty.
                **{l.name: l for l in node_labels.vanished},
                **{l.name: l for l in node_labels.present},
            }
        )
    return list(nodes_host_labels.values())


def analyse_host_labels(
    host_name: HostName,
    *,
    discovered_host_labels: Sequence[HostLabel],
    existing_host_labels: Sequence[HostLabel],
    ruleset_matcher: RulesetMatcher,
    save_labels: bool,
) -> QualifiedDiscovery[HostLabel]:
    host_labels = QualifiedDiscovery[HostLabel](
        preexisting=existing_host_labels,
        current=discovered_host_labels,
        key=lambda hl: hl.label,
    )

    if save_labels:
        do_save_labels(host_name, host_labels)

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
        # In the first step 'discover_host_labels' the ruleset optimizer caches the
        # result of the evaluation of these rules. Contemporary we may find new host
        # labels which are not yet taken into account by the ruleset optimizer.
        # In the next step '_discover_services' we want to discover new services
        # based on these new host labels but we only got the cached result.
        # If we found new host labels, we have to evaluate these rules again in order
        # to find new services, eg. in 'inventory_df'. Thus we have to clear these caches.
        ruleset_matcher.clear_caches()

    return host_labels


def do_load_labels(host_name: HostName) -> Sequence[HostLabel]:
    raw_label_dict = DiscoveredHostLabelsStore(host_name).load()
    return [HostLabel.from_dict(name, value) for name, value in raw_label_dict.items()]


def do_save_labels(host_name: HostName, host_labels: QualifiedDiscovery[HostLabel]) -> None:
    DiscoveredHostLabelsStore(host_name).save(
        {
            # TODO (mo): I'm not sure this is desired. If it is, it should be explained.
            # Whenever we do not load the host labels, vanished will be empty.
            **{l.name: l.to_dict() for l in host_labels.vanished},
            **{l.name: l.to_dict() for l in host_labels.present},
        }
    )


def discover_host_labels(
    host_name: HostName,
    host_label_plugins: Mapping[SectionName, HostLabelDiscoveryPlugin],
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
    host_label_plugins: Mapping[SectionName, HostLabelDiscoveryPlugin],
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
            host_label_params = host_label_plugin.parameters(host_key.hostname)
            if host_label_params is not None:
                kwargs["params"] = host_label_params

            try:
                for label in host_label_plugin.function(**kwargs):
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
