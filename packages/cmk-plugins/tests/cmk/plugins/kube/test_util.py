# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

import pytest

from cmk.plugins.kube.util import map_optional


@pytest.mark.parametrize(
    "fn, val, out",
    [
        (lambda x: x + 3, None, None),
        (lambda x: x + 3, 26, 29),
        (list, (1, 2, 3), [1, 2, 3]),
        (list, None, None),
    ],
)
def test_map_optional[T, U](fn: Callable[[T], U], val: T, out: U) -> None:
    assert map_optional(fn, val) == out
