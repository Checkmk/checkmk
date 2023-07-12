#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from typing import Generic, TypeVar

from .type_defs import SectionNameCollection

__all__ = ["Parser"]

_Tin = TypeVar("_Tin")
_Tout = TypeVar("_Tout")


class Parser(Generic[_Tin, _Tout], abc.ABC):
    """Parse raw data into host sections."""

    @abc.abstractmethod
    def parse(self, raw_data: _Tin, *, selection: SectionNameCollection) -> _Tout:
        raise NotImplementedError
