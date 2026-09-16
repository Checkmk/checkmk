#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pydantic import BaseModel

from cmk.gui.type_defs import SizeMM


class GraphRanges(BaseModel, frozen=True):
    time_range: tuple[int, int]
    step: int
    vertical_range: tuple[float, float] | None = None


def compute_graph_ranges_for_width(width: SizeMM, start_time: int, end_time: int) -> GraphRanges:
    graph_offcut_width = 20.0
    mm_per_step = 0.5

    available_width = width - graph_offcut_width
    number_of_steps = int(available_width / mm_per_step)
    step = int((end_time - start_time) / number_of_steps / 2)
    return GraphRanges(time_range=(start_time, end_time), step=step)
