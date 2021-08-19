#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
from typing import cast, Generic, List, Mapping, MutableMapping, Optional, Sequence, Tuple, TypeVar

from cmk.utils.type_defs import HostName, SectionName

from cmk.core_helpers.cache import TRawDataSection

THostSections = TypeVar("THostSections", bound="HostSections")


# TODO(ml): make this container properly immutable.
class HostSections(Generic[TRawDataSection], metaclass=abc.ABCMeta):
    """Host informations from the sources."""
    def __init__(
        self,
        sections: Optional[MutableMapping[SectionName, TRawDataSection]] = None,
        *,
        cache_info: Optional[MutableMapping[SectionName, Tuple[int, int]]] = None,
        # For `piggybacked_raw_data`, List[bytes] is equivalent to AgentRawData.
        piggybacked_raw_data: Optional[MutableMapping[HostName, List[bytes]]] = None,
    ) -> None:
        super().__init__()
        self._sections = sections if sections else {}
        self._cache_info = cache_info if cache_info else {}
        self._piggybacked_raw_data = piggybacked_raw_data if piggybacked_raw_data else {}

    @property
    def sections(self) -> Mapping[SectionName, TRawDataSection]:
        return self._sections

    @property
    def cache_info(self) -> Mapping[SectionName, Tuple[int, int]]:
        return self._cache_info

    @property
    def piggybacked_raw_data(self) -> Mapping[HostName, Sequence[bytes]]:
        return self._piggybacked_raw_data

    def __repr__(self):
        return "%s(sections=%r, cache_info=%r, piggybacked_raw_data=%r)" % (
            type(self).__name__,
            self.sections,
            self.cache_info,
            self.piggybacked_raw_data,
        )

    def __add__(self, other: HostSections) -> HostSections:
        for section_name, section_content in other.sections.items():
            self._sections.setdefault(
                section_name,
                cast(TRawDataSection, []),
            ).extend(section_content)

        for hostname, raw_lines in other.piggybacked_raw_data.items():
            self._piggybacked_raw_data.setdefault(hostname, []).extend(raw_lines)

        # TODO: It should be supported that different sources produce equal sections.
        # this is handled for the self.sections data by simply concatenating the lines
        # of the sections, but for the self.cache_info this is not done. Why?
        # TODO: checking._execute_check() is using the oldest cached_at and the largest interval.
        #       Would this be correct here?
        self._cache_info.update(other.cache_info)

        return self
