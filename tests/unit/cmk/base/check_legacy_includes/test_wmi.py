#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.check_legacy_includes.wmi import scale_counter


def scale_counter_reference(measure, factor, base):
    # old, inefficient implementation
    # takes ages for the arguments: 18446744073664412644, 1, 15143722
    while (base * factor) < measure:
        base += 1 << 32
    return float(measure) / base


@pytest.mark.parametrize('measure, factor, base', [
    (1, 1, 1),
    (2, 1, 1),
    (3, 2, 1),
    ((1 << 32) - 1, 1, 1),
    (1 + (1 << 32), 1, 1),
    (1844674407, 1, 15143722),
    (1844674407, 2, 15143722),
    (1844674407, 13, 15143727),
    (1844674407366441, 1, 15143722),
])
def test_scale_counter(measure, factor, base):
    assert 1e-15 > abs(
        scale_counter(measure, factor, base) - scale_counter_reference(measure, factor, base))
