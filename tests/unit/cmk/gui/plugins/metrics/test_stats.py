#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from cmk.gui.plugins.metrics import stats


@pytest.mark.parametrize("q, array, result", [
    (50, [1], 1),
    (50, [1, 5, 6], 5),
    (50, [1, 5, 6, 6], 5.5),
    (100, [1, 5, 6, 6], 6),
    (100, [1, 5, 6], 6),
    (100, [1, 5, 6, 7], 7),
    (75, [1, 5, 6, 7], 6.5),
    (0, [1, 5, 6, 7], 1),
])
def test_percentile(q, array, result):
    assert stats.percentile(array, q) == result
