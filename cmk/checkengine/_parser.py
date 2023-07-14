#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
from collections.abc import Mapping, Sequence
from typing import Final, Generic, TypeVar

from cmk.utils.hostaddress import HostName
from cmk.utils.sectionname import SectionMap

from .type_defs import SectionNameCollection

__all__ = ["Parser", "HostSections"]

_Tin = TypeVar("_Tin")
_Tout = TypeVar("_Tout", bound=SectionMap[Sequence])


class HostSections(Generic[_Tout]):
    """Host informations from the sources."""

    def __init__(
        self,
        sections: _Tout,
        *,
        cache_info: SectionMap[tuple[int, int]] | None = None,
        # For `piggybacked_raw_data`, Sequence[bytes] is equivalent to AgentRawData.
        piggybacked_raw_data: Mapping[HostName, Sequence[bytes]] | None = None,
    ) -> None:
        super().__init__()
        self.sections = sections
        self.cache_info: Final = cache_info if cache_info else {}
        self.piggybacked_raw_data: Final = piggybacked_raw_data if piggybacked_raw_data else {}


class Parser(Generic[_Tin, _Tout], abc.ABC):
    """Parse raw data into host sections."""

    @abc.abstractmethod
    def parse(self, raw_data: _Tin, *, selection: SectionNameCollection) -> HostSections[_Tout]:
        raise NotImplementedError
