#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
from collections.abc import Sequence

import pytest

from cmk.gui.config import active_config
from cmk.gui.http import request
from cmk.gui.type_defs import Row
from cmk.gui.views.perfometer.base import Perfometer
from cmk.gui.views.perfometer.sorter import SorterPerfometer


@pytest.mark.parametrize(
    "sort_values",
    [
        [-1, 1, 0, None],
        [None, 0, 1, -1],
        [1, None, 0, -1],
    ],
)
def test_cmp_of_missing_values(sort_values: Sequence[float | None], request_context: None) -> None:
    """If perfometer values are missing, sort_value() of Perfometer will return (None, None).
    The sorting chosen below is consistent with how _data_sort from cmk.gui.views.__init__.py
    treats missing values."""
    data = [
        {
            "service_check_command": "check_mk-kube_memory",
            "service_perf_data": (
                "kube_memory_request=209715200;;;0;"
                if v is None
                else f"kube_memory_usage={v};;;0; kube_memory_request=209715200;;;;"
            ),
        }
        for v in sort_values
    ]

    def wrapped(r1: Row, r2: Row) -> int:
        return SorterPerfometer.cmp(r1, r2, parameters=None, config=active_config, request=request)

    data.sort(key=functools.cmp_to_key(wrapped))
    assert [Perfometer(r).sort_value()[1] for r in data] == [None, -1.0, 0.0, 1.0]
