#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import copy
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Final, Generic

from cmk.utils.hostaddress import HostName
from cmk.utils.type_defs import SectionName

from cmk.fetchers.cache import TRawDataSection


class HostSections(Generic[TRawDataSection], abc.ABC):
    """Host informations from the sources."""

    def __init__(
        self,
        sections: Mapping[SectionName, Sequence[TRawDataSection]] | None = None,
        *,
        cache_info: Mapping[SectionName, tuple[int, int]] | None = None,
        # For `piggybacked_raw_data`, Sequence[bytes] is equivalent to AgentRawData.
        piggybacked_raw_data: Mapping[HostName, Sequence[bytes]] | None = None,
    ) -> None:
        super().__init__()
        self.sections: Mapping[SectionName, Sequence[TRawDataSection]] = (
            sections if sections else {}
        )
        self.cache_info: Final = cache_info if cache_info else {}
        self.piggybacked_raw_data: Final = piggybacked_raw_data if piggybacked_raw_data else {}

    def __repr__(self) -> str:
        return "{}(sections={!r}, cache_info={!r}, piggybacked_raw_data={!r})".format(
            type(self).__name__,
            self.sections,
            self.cache_info,
            self.piggybacked_raw_data,
        )

    def __add__(self, other: HostSections[TRawDataSection]) -> HostSections[TRawDataSection]:
        new_sections = copy.deepcopy(dict(self.sections))
        for section_name, section_content in other.sections.items():
            s = new_sections.get(section_name)
            new_sections[section_name] = (
                (list(s) + list(section_content)) if s else list(section_content)
            )

        new_piggybacked_raw_data: MutableMapping[HostName, list[bytes]] = {
            k: list(v) for k, v in self.piggybacked_raw_data.items()
        }
        for hostname, raw_lines in other.piggybacked_raw_data.items():
            new_piggybacked_raw_data.setdefault(hostname, []).extend(raw_lines)

        # TODO: It should be supported that different sources produce equal sections.
        # this is handled for the self.sections data by simply concatenating the lines
        # of the sections, but for the self.cache_info this is not done. Why?
        # TODO: checking._execute_check() is using the oldest cached_at and the largest interval.
        #       Would this be correct here?
        new_cache_info = dict(self.cache_info)
        new_cache_info.update(other.cache_info)

        return HostSections[TRawDataSection](
            new_sections,
            cache_info=new_cache_info,
            piggybacked_raw_data=new_piggybacked_raw_data,
        )

    def __bool__(self) -> bool:
        # This is needed in order to decide whether a host has inventory data or not, see:
        # cmk.base.agent_based.inventory._inventory.py::_no_data_or_files
        return bool(self.sections) or bool(self.piggybacked_raw_data)
