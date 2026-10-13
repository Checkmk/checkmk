#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The quantity layer of the plug-in API, shared by graphs and perfometers."""

import pytest

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v2_unstable import metrics as metrics_v2_unstable
from cmk.graphing_engine import ScalarKind
from cmk.graphing_engine._api_plugins import ApiScalar
from cmk.graphing_engine._quantity_from_api import scalar_kind_of


@pytest.mark.parametrize(
    "scalar, expected",
    [
        (metrics_v1.WarningOf("a"), ScalarKind.WARNING),
        (metrics_v1.CriticalOf("a"), ScalarKind.CRITICAL),
        (metrics_v2_unstable.LowerWarningOf("a"), ScalarKind.LOWER_WARNING),
        (metrics_v2_unstable.LowerCriticalOf("a"), ScalarKind.LOWER_CRITICAL),
        (metrics_v1.MinimumOf("a", color=metrics_v1.Color.BLUE), ScalarKind.MINIMUM),
        (metrics_v1.MaximumOf("a", color=metrics_v1.Color.BLUE), ScalarKind.MAXIMUM),
    ],
)
def test_scalar_kind_of(scalar: ApiScalar, expected: ScalarKind) -> None:
    assert scalar_kind_of(scalar) == expected
