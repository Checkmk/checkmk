#!/usr/bin/env python3
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import OrderedDict
from typing import Mapping, Sequence

from pydantic import BaseModel

Section = OrderedDict

CounterValues = Sequence[str]
SubSectionCounter = Mapping[str, list[tuple[CounterValues, str]]]
SectionCounter = Mapping[str, SubSectionCounter]


class ESXVm(BaseModel):
    snapshots: Sequence[str]


SectionVM = ESXVm | None


def average_parsed_data(values: CounterValues) -> float:
    """
    >>> average_parsed_data(['1', '2'])
    1.5
    >>> average_parsed_data(['1'])
    1.0
    >>> average_parsed_data([])
    0
    """
    return sum(map(int, values)) / len(values) if values else 0
