#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Discovery of HostLabels."""
from collections.abc import Iterable, Mapping, Sequence
from typing import TypeVar

from cmk.utils.exceptions import MKGeneralException, MKTimeout, OnError
from cmk.utils.labels import HostLabel
from cmk.utils.log import console
from cmk.utils.rulesets.ruleset_matcher import merge_cluster_labels
from cmk.utils.type_defs import HostName, SectionName

from cmk.checkers import HostKey, HostLabelDiscoveryPlugin, SourceType
from cmk.checkers.sectionparser import Provider, ResolvedResult

from .utils import QualifiedDiscovery

__all__ = [
    "analyse_cluster_labels",
    "discover_host_labels",
]


def analyse_cluster_labels(
    cluster_name: HostName,
    node_names: Sequence[HostName],
    *,
    discovered_host_labels: Mapping[HostName, Sequence[HostLabel]],
    existing_host_labels: Mapping[HostName, Sequence[HostLabel]],
) -> tuple[QualifiedDiscovery[HostLabel], Mapping[HostName, Sequence[HostLabel]]]:
    kept_labels = {
        node_name: QualifiedDiscovery[HostLabel](
            preexisting=existing_host_labels.get(node_name, ()),
            current=discovered_host_labels.get(node_name, ()),
        ).kept()
        for node_name in node_names
    }

    cluster_labels = QualifiedDiscovery[HostLabel](
        preexisting=merge_cluster_labels(
            nodes_labels for node in node_names if (nodes_labels := existing_host_labels.get(node))
        ),
        current=merge_cluster_labels(
            nodes_labels for node in node_names if (nodes_labels := kept_labels.get(node))
        ),
    )
    kept_labels[cluster_name] = cluster_labels.kept()

    return cluster_labels, kept_labels


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
        for section_name, section_data, _cache_info in _sort_sections_by_label_priority(
            parsed_results
        ):
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


_TupleT = TypeVar("_TupleT", bound=tuple[object, ...])


def _sort_sections_by_label_priority(sections: Iterable[_TupleT]) -> Sequence[_TupleT]:
    """
    `snmp_info`` sets a couple of host labels for device type but should not overwrite device specific ones.
    We put the snmp_info section first.
    """
    return sorted(sections, key=lambda t: (str(t[0]) != "snmp_info", str(t[0])))
