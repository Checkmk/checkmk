#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping

from cmk.ccc.hostaddress import HostName

from cmk.utils.sectionname import MutableSectionMap

from cmk.checkengine.fetcher import HostKey

from ._parser import HostSections

__all__ = ["group_by_host"]


def group_by_host(
    host_sections: Iterable[tuple[HostKey, HostSections]], log: Callable[[str], None]
) -> Mapping[HostKey, HostSections]:
    out_sections: dict[HostKey, MutableSectionMap[list]] = defaultdict(dict)
    out_cache_info: dict[HostKey, MutableSectionMap[tuple[int, int]]] = defaultdict(dict)
    out_piggybacked_raw_data: dict[HostKey, dict[HostName, list[bytes]]] = defaultdict(dict)
    host_keys: list[HostKey] = []

    for host_key, host_section in host_sections:
        host_keys.append(host_key)
        section_names = sorted(str(s) for s in host_section.sections.keys())
        log(f"  {host_key!s}  -> Add sections: {section_names}")
        for section_name, section_content in host_section.sections.items():
            out_sections[host_key].setdefault(section_name, []).extend(section_content)
        for hostname, raw_lines in host_section.piggybacked_raw_data.items():
            out_piggybacked_raw_data[host_key].setdefault(hostname, []).extend(raw_lines)
        # TODO: It should be supported that different sources produce equal sections.
        # this is handled for the output[host_key].sections data by simply concatenating the lines
        # of the sections, but for the output[host_key].cache_info this is not done. Why?
        # TODO: checking._execute_check() is using the oldest cached_at and the largest interval.
        #       Would this be correct here?
        out_cache_info[host_key].update(host_section.cache_info)

    return {
        hk: HostSections(
            out_sections[hk],
            cache_info=out_cache_info[hk],
            piggybacked_raw_data=out_piggybacked_raw_data[hk],
        )
        for hk in host_keys
    }
