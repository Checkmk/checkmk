#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from typing import cast, Generic, List, MutableMapping, Optional, Tuple, TypeVar

from cmk.utils.type_defs import HostName, SectionName

from cmk.core_helpers.cache import TRawDataSection

THostSections = TypeVar("THostSections", bound="HostSections")


class HostSections(Generic[TRawDataSection], metaclass=abc.ABCMeta):
    """A wrapper class for the host information read by the data sources

    It contains the following information:

        1. sections:                A dictionary from section_name to a list of rows,
                                    the section content
        2. piggybacked_raw_data:    piggy-backed data for other hosts
        3. cache_info:              Agent cache information
                                    (dict section name -> (cached_at, cache_interval))
    """
    def __init__(
        self,
        sections: Optional[MutableMapping[SectionName, TRawDataSection]] = None,
        *,
        cache_info: Optional[MutableMapping[SectionName, Tuple[int, int]]] = None,
        # For `piggybacked_raw_data`, List[bytes] is equivalent to AgentRawData.
        piggybacked_raw_data: Optional[MutableMapping[HostName, List[bytes]]] = None,
    ) -> None:
        super().__init__()
        self.sections = sections if sections else {}
        self.cache_info = cache_info if cache_info else {}
        self.piggybacked_raw_data = piggybacked_raw_data if piggybacked_raw_data else {}

    def __repr__(self):
        return "%s(sections=%r, cache_info=%r, piggybacked_raw_data=%r)" % (
            type(self).__name__,
            self.sections,
            self.cache_info,
            self.piggybacked_raw_data,
        )

    # TODO: It should be supported that different sources produce equal sections.
    # this is handled for the self.sections data by simply concatenating the lines
    # of the sections, but for the self.cache_info this is not done. Why?
    # TODO: checking._execute_check() is using the oldest cached_at and the largest interval.
    #       Would this be correct here?
    def add(self, host_sections: "HostSections") -> None:
        """Add the content of `host_sections` to this HostSection."""
        for section_name, section_content in host_sections.sections.items():
            self.sections.setdefault(
                section_name,
                cast(TRawDataSection, []),
            ).extend(section_content)

        for hostname, raw_lines in host_sections.piggybacked_raw_data.items():
            self.piggybacked_raw_data.setdefault(hostname, []).extend(raw_lines)

        if host_sections.cache_info:
            self.cache_info.update(host_sections.cache_info)
