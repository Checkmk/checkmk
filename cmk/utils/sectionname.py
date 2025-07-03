#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import NewType, TypeAlias, TypeVar

__all__ = ["SectionName", "SectionMap"]


SectionName = NewType("SectionName", str)


_T_co = TypeVar("_T_co", covariant=True)
SectionMap: TypeAlias = Mapping[SectionName, _T_co]

_T = TypeVar("_T")
MutableSectionMap: TypeAlias = MutableMapping[SectionName, _T]
