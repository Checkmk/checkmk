#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from typing import Generic, TypeVar

from cmk.fetchers.cache import TRawDataSection

from .host_sections import HostSections
from .type_defs import SectionNameCollection

__all__ = ["Parser"]

_TRawData = TypeVar("_TRawData")


class Parser(Generic[_TRawData, TRawDataSection], abc.ABC):
    """Parse raw data into host sections."""

    @abc.abstractmethod
    def parse(
        self, raw_data: _TRawData, *, selection: SectionNameCollection
    ) -> HostSections[TRawDataSection]:
        raise NotImplementedError
