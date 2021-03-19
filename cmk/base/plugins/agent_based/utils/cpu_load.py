#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Tuple, TypedDict, NamedTuple
from enum import Enum


class Load(NamedTuple):
    load1: float
    load5: float
    load15: float


class LoadParams(TypedDict):
    levels: Tuple[float, float]


class ProcessorType(Enum):
    unspecified = 0
    physical = 1
    logical = 2
