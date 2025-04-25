#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Discovery of HostLabels."""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import TypeVar

from cmk.ccc.exceptions import MKGeneralException, MKTimeout, OnError
from cmk.ccc.hostaddress import HostName

from cmk.utils.labels import HostLabel as _HostLabel
from cmk.utils.labels import merge_cluster_labels
from cmk.utils.log import console
from cmk.utils.sectionname import SectionMap

from cmk.checkengine.discovery._utils import QualifiedDiscovery
from cmk.checkengine.fetcher import HostKey, SourceType
from cmk.checkengine.parameters import Parameters
from cmk.checkengine.sectionparser import Provider, ResolvedResult

from cmk.agent_based.v1 import HostLabel

__all__ = [
    "analyse_cluster_labels",
    "discover_host_labels",
    "HostLabel",
    "HostLabelPlugin",
]


@dataclass(frozen=True)
class HostLabelPlugin:
    function: Callable[..., Iterator[HostLabel]]
    parameters: Callable[[HostName], Sequence[Parameters] | Parameters | None]

    @classmethod
    def trivial(cls) -> HostLabelPlugin:
        return cls(function=lambda *a, **kw: iter(()), parameters=lambda _: None)


def analyse_cluster_labels(
    cluster_name: HostName,
    node_names: Sequence[HostName],
    *,
    discovered_host_labels: Mapping[HostName, Sequence[_HostLabel]],
    existing_host_labels: Mapping[HostName, Sequence[_HostLabel]],
) -> tuple[QualifiedDiscovery[_HostLabel], Mapping[HostName, Sequence[_HostLabel]]]:
    kept_labels = {
        node_name: QualifiedDiscovery[_HostLabel](
            preexisting=existing_host_labels.get(node_name, ()),
            current=discovered_host_labels.get(node_name, ()),
        ).present
        for node_name in node_names
    }

    cluster_labels = QualifiedDiscovery[_HostLabel](
        preexisting=merge_cluster_labels(
            nodes_labels for node in node_names if (nodes_labels := existing_host_labels.get(node))
        ),
        current=merge_cluster_labels(
            nodes_labels for node in node_names if (nodes_labels := kept_labels.get(node))
        ),
    )
    kept_labels[cluster_name] = cluster_labels.present

    return cluster_labels, kept_labels


def discover_host_labels(
    node_name: HostName,
    host_label_plugins: SectionMap[HostLabelPlugin],
    *,
    providers: Mapping[HostKey, Provider],
    on_error: OnError,
) -> Sequence[_HostLabel]:
    """Discover host labels for a node.

    This function makes no sense to be called for a cluster.
    """
    # make names unique
    labels_by_name = {
        **_discover_host_labels_for_source_type(
            host_label_plugins,
            host_key=HostKey(node_name, SourceType.HOST),
            providers=providers,
            on_error=on_error,
        ),
        **_discover_host_labels_for_source_type(
            host_label_plugins,
            host_key=HostKey(node_name, SourceType.MANAGEMENT),
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
    host_label_plugins: SectionMap[HostLabelPlugin],
    *,
    host_key: HostKey,
    providers: Mapping[HostKey, Provider],
    on_error: OnError,
) -> Mapping[str, _HostLabel]:
    """This function only makes sense to be called for a node (not a cluster)."""
    host_labels = {}
    try:
        parsed_results = _all_parsing_results(host_key, providers)

        names = ", ".join(str(r.section_name) for r in parsed_results)
        console.debug(f"Trying host label discovery with: {names}")
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
                    console.debug(f"  {label.name}: {label.value} ({section_name})")
                    host_labels[label.name] = _HostLabel(label.name, label.value, section_name)
            except (KeyboardInterrupt, MKTimeout):
                raise
            except Exception as exc:
                if on_error is OnError.RAISE:
                    raise
                if on_error is OnError.WARN:
                    console.error(
                        f"Host label discovery of '{section_name}' failed: {exc}",
                        file=sys.stderr,
                    )

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
