#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import typing
from typing import Final, Generic, Mapping, Optional, Sequence, Tuple

from cmk.utils.type_defs import HostName, SectionName

from cmk.core_helpers.cache import TRawDataSection


class HostSections(Generic[TRawDataSection], abc.ABC):
    """Host informations from the sources."""

    def __init__(
        self,
        sections: Optional[Mapping[SectionName, Sequence[TRawDataSection]]] = None,
        *,
        cache_info: Optional[Mapping[SectionName, Tuple[int, int]]] = None,
        # For `piggybacked_raw_data`, Sequence[bytes] is equivalent to AgentRawData.
        piggybacked_raw_data: Optional[Mapping[HostName, Sequence[bytes]]] = None,
    ) -> None:
        super().__init__()
        self.sections: Final = sections if sections else {}
        self.cache_info: Final = cache_info if cache_info else {}
        self.piggybacked_raw_data: Final = piggybacked_raw_data if piggybacked_raw_data else {}

    def __repr__(self):
        return "%s(sections=%r, cache_info=%r, piggybacked_raw_data=%r)" % (
            type(self).__name__,
            self.sections,
            self.cache_info,
            self.piggybacked_raw_data,
        )

    @typing.no_type_check
    def __add__(self, other: HostSections[TRawDataSection]) -> HostSections[TRawDataSection]:
        for section_name, section_content in other.sections.items():
            self.sections.setdefault(section_name, []).extend(section_content)
        for hostname, raw_lines in other.piggybacked_raw_data.items():
            self.piggybacked_raw_data.setdefault(hostname, []).extend(raw_lines)
        # TODO: It should be supported that different sources produce equal sections.
        # this is handled for the self.sections data by simply concatenating the lines
        # of the sections, but for the self.cache_info this is not done. Why?
        # TODO: checking._execute_check() is using the oldest cached_at and the largest interval.
        #       Would this be correct here?
        self.cache_info.update(other.cache_info)
        return self
