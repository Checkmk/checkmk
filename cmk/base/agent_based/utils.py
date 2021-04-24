#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, MutableMapping, Sequence

from cmk.utils.type_defs import HostKey, ParsedSectionName

from .data_provider import ParsedSectionsBroker

_ParsedSectionContent = Any


def get_section_kwargs(
    parsed_sections_broker: ParsedSectionsBroker,
    host_key: HostKey,
    parsed_section_names: Sequence[ParsedSectionName],
) -> MutableMapping[str, _ParsedSectionContent]:
    """Prepares section keyword arguments for a non-cluster host

    It returns a dictionary containing one entry (may be None) for each
    of the required sections, or an empty dictionary if no data was found at all.
    """
    keys = (["section"]
            if len(parsed_section_names) == 1 else ["section_%s" % s for s in parsed_section_names])

    kwargs = {
        key: parsed_sections_broker.get_parsed_section(host_key, parsed_section_name)
        for key, parsed_section_name in zip(keys, parsed_section_names)
    }
    # empty it, if nothing was found:
    if all(v is None for v in kwargs.values()):
        kwargs.clear()

    return kwargs


def get_section_cluster_kwargs(
    parsed_sections_broker: ParsedSectionsBroker,
    node_keys: Sequence[HostKey],
    parsed_section_names: Sequence[ParsedSectionName],
) -> MutableMapping[str, MutableMapping[str, _ParsedSectionContent]]:
    """Prepares section keyword arguments for a cluster host

    It returns a dictionary containing one optional dictionary[Host, ParsedSection]
    for each of the required sections, or an empty dictionary if no data was found at all.
    """
    kwargs: MutableMapping[str, MutableMapping[str, Any]] = {}
    for node_key in node_keys:
        node_kwargs = get_section_kwargs(parsed_sections_broker, node_key, parsed_section_names)
        for key, sections_node_data in node_kwargs.items():
            kwargs.setdefault(key, {})[node_key.hostname] = sections_node_data
    # empty it, if nothing was found:
    if all(v is None for s in kwargs.values() for v in s.values()):
        kwargs.clear()

    return kwargs
