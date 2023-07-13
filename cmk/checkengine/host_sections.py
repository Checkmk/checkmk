#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
from collections.abc import Mapping, Sequence
from typing import Final, Generic, TypeVar

from cmk.utils.hostaddress import HostName
from cmk.utils.sectionname import HostSection, SectionName

_T = TypeVar("_T", bound=HostSection[Sequence])


class HostSections(Generic[_T], abc.ABC):
    """Host informations from the sources."""

    def __init__(
        self,
        sections: _T,
        *,
        cache_info: Mapping[SectionName, tuple[int, int]] | None = None,
        # For `piggybacked_raw_data`, Sequence[bytes] is equivalent to AgentRawData.
        piggybacked_raw_data: Mapping[HostName, Sequence[bytes]] | None = None,
    ) -> None:
        super().__init__()
        self.sections = sections
        self.cache_info: Final = cache_info if cache_info else {}
        self.piggybacked_raw_data: Final = piggybacked_raw_data if piggybacked_raw_data else {}

    def __repr__(self) -> str:
        return "{}(sections={!r}, cache_info={!r}, piggybacked_raw_data={!r})".format(
            type(self).__name__,
            self.sections,
            self.cache_info,
            self.piggybacked_raw_data,
        )

    def __bool__(self) -> bool:
        # This is needed in order to decide whether a host has inventory data or not, see:
        # cmk.base.agent_based.inventory._inventory.py::_no_data_or_files
        return bool(self.sections) or bool(self.piggybacked_raw_data)
