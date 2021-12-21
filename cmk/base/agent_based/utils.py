#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Iterable, Mapping, Optional, Sequence

from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.type_defs import HostKey, ParsedSectionName, ServiceState

from cmk.core_helpers.type_defs import Mode

from .data_provider import ParsedSectionContent, ParsedSectionsBroker, SourceResults

_SectionKwargs = Mapping[str, ParsedSectionContent]


def get_section_kwargs(
    parsed_sections_broker: ParsedSectionsBroker,
    host_key: HostKey,
    parsed_section_names: Sequence[ParsedSectionName],
) -> _SectionKwargs:
    """Prepares section keyword arguments for a non-cluster host

    It returns a dictionary containing one entry (may be None) for each
    of the required sections, or an empty dictionary if no data was found at all.
    """
    keys = (
        ["section"]
        if len(parsed_section_names) == 1
        else ["section_%s" % s for s in parsed_section_names]
    )

    kwargs = {
        key: parsed_sections_broker.get_parsed_section(host_key, parsed_section_name)
        for key, parsed_section_name in zip(keys, parsed_section_names)
    }
    # empty it, if nothing was found:
    if all(v is None for v in kwargs.values()):
        return {}

    return kwargs


def get_section_cluster_kwargs(
    parsed_sections_broker: ParsedSectionsBroker,
    node_keys: Sequence[HostKey],
    parsed_section_names: Sequence[ParsedSectionName],
) -> Mapping[str, _SectionKwargs]:
    """Prepares section keyword arguments for a cluster host

    It returns a dictionary containing one optional dictionary[Host, ParsedSection]
    for each of the required sections, or an empty dictionary if no data was found at all.
    """
    kwargs: Dict[str, Dict[str, ParsedSectionContent]] = {}
    for node_key in node_keys:
        node_kwargs = get_section_kwargs(parsed_sections_broker, node_key, parsed_section_names)
        for key, sections_node_data in node_kwargs.items():
            kwargs.setdefault(key, {})[node_key.hostname] = sections_node_data
    # empty it, if nothing was found:
    if all(v is None for s in kwargs.values() for v in s.values()):
        return {}

    return kwargs


def check_sources(
    *,
    source_results: SourceResults,
    mode: Mode,
    include_ok_results: bool = False,
    override_non_ok_state: Optional[ServiceState] = None,
) -> Iterable[ActiveCheckResult]:
    for source, host_sections in source_results:
        subresults = source.summarize(host_sections, mode=mode)
        if include_ok_results or any(s.state != 0 for s in subresults):
            yield from (
                ActiveCheckResult(
                    s.state if override_non_ok_state is None else override_non_ok_state,
                    f"[{source.id}] {s.summary}",
                    s.details,
                    s.metrics,
                )
                for s in subresults[:1]
            )
            yield from (
                ActiveCheckResult(
                    s.state if override_non_ok_state is None else override_non_ok_state,
                    s.summary,
                    s.details,
                    s.metrics,
                )
                for s in subresults[1:]
            )


def check_parsing_errors(
    errors: Sequence[str],
    *,
    error_state: ServiceState = 1,
) -> Sequence[ActiveCheckResult]:
    state = error_state if errors else 0
    return [ActiveCheckResult(state, msg.split(" - ")[0], (msg,)) for msg in errors]
