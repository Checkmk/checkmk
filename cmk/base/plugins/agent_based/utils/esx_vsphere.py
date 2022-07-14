#!/usr/bin/env python3
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import OrderedDict
from typing import Mapping, Sequence

Section = OrderedDict
SectionVM = dict[str, list[str]]

CounterValues = Sequence[str]
SubSectionCounter = Mapping[str, list[tuple[CounterValues, str]]]
SectionCounter = Mapping[str, SubSectionCounter]
