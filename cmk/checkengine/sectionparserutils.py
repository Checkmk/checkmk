#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from typing import Final, NamedTuple

from .checkresults import ActiveCheckResult
from .fetcher import HostKey
from .sectionparser import ParsedSectionContent, ParsedSectionName, Provider
from .submitters import ServiceState

_SectionKwargs = Mapping[str, ParsedSectionContent | None]


class _NoParsedData(NamedTuple):
    parsed_data: None = None


_NO_PARSED_DATA: Final = _NoParsedData()


def get_section_kwargs(
    providers: Mapping[HostKey, Provider],
    host_key: HostKey,
    parsed_section_names: Sequence[ParsedSectionName],
) -> _SectionKwargs:
    """Prepares section keyword arguments for a non-cluster host

    It returns a dictionary containing one entry (may be None) for each
    of the required sections, or an empty dictionary if no data was found at all.
    """
    try:
        resolver = providers[host_key]
    except KeyError:
        return {}

    resolved_map = {
        name: resolved
        for name in parsed_section_names
        if (resolved := resolver.resolve(name)) is not None
    }

    if not resolved_map:
        return {}

    return {
        "section" if len(parsed_section_names) == 1 else f"section_{name}": resolved_map.get(
            name, _NO_PARSED_DATA
        ).parsed_data
        for name in parsed_section_names
    }


def get_section_cluster_kwargs(
    providers: Mapping[HostKey, Provider],
    node_keys: Sequence[HostKey],
    parsed_section_names: Sequence[ParsedSectionName],
) -> Mapping[str, _SectionKwargs]:
    """Prepares section keyword arguments for a cluster host

    It returns a dictionary containing one optional dictionary[Host, ParsedSection]
    for each of the required sections, or an empty dictionary if no data was found at all.
    """
    kwargs: dict[str, dict[str, ParsedSectionContent]] = {}
    for node_key in node_keys:
        node_kwargs = get_section_kwargs(providers, node_key, parsed_section_names)
        for key, sections_node_data in node_kwargs.items():
            kwargs.setdefault(key, {})[node_key.hostname] = sections_node_data
    # empty it, if nothing was found:
    if all(v is None for s in kwargs.values() for v in s.values()):
        return {}

    return kwargs


def check_parsing_errors(
    errors: Iterable[str],
    *,
    error_state: ServiceState = 1,
) -> Sequence[ActiveCheckResult]:
    return [ActiveCheckResult(error_state, msg.split(" - ")[0], (msg,)) for msg in errors]


_CacheInfo = tuple[int, int]


def get_cache_info(cache_infos: Sequence[_CacheInfo]) -> _CacheInfo | None:
    # TODO: should't the host key be provided here?
    """Aggregate information about the age of the data in the agent sections"""
    if not cache_infos:
        return None

    return (
        min(ats for ats, _intervals in cache_infos),
        max(intervals for _ats, intervals in cache_infos),
    )
