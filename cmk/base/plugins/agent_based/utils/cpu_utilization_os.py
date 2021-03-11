#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple


class SectionCpuUtilizationOs(NamedTuple):
    num_cpus: int
    # time_base and time_cpu have to have the same unit!
    # either both seconds, or both ticks, or both micro seconds
    time_base: float
    # time base has to be independent of num_cpus! so if you use system_ticks
    # as time_base you may have to divide it by the number of cpus
    time_cpu: float
