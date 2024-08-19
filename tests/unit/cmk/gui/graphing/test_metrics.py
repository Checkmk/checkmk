#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import Counter
from typing import Literal

from cmk.gui.graphing._metrics import _get_legacy_metric_info


def test__get_legacy_metric_info() -> None:
    color_counter: Counter[Literal["metric", "predictive"]] = Counter()
    assert _get_legacy_metric_info("foo", color_counter) == {
        "title": "Foo",
        "unit": "",
        "color": "12/a",
    }
    assert _get_legacy_metric_info("bar", color_counter) == {
        "title": "Bar",
        "unit": "",
        "color": "13/a",
    }
    assert color_counter["metric"] == 2
