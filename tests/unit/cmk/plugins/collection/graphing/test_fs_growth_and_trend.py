#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import metrics, translations
from cmk.plugins.collection.graphing.fs_growth_and_trend import metric_fs_growth, metric_fs_trend
from cmk.plugins.collection.graphing.translations import translation_filesystem_storages_df

# The df check emits growth/trend in MB/day (packages/cmk-plugins/cmk/plugins/lib/size_trend.py).
_BYTES_PER_MB = 1048576


@pytest.mark.parametrize(
    "metric, raw_metric_name",
    [
        pytest.param(metric_fs_growth, "growth", id="growth"),
        pytest.param(metric_fs_trend, "trend", id="trend"),
    ],
)
@pytest.mark.xfail(
    reason=(
        "SUP-29835: the growth/trend translation scales MB/day by MB/86400, producing "
        "bytes/second, but the metric is declared as bytes/day. The graph therefore shows "
        "a far smaller unit than the check summary."
    ),
    strict=True,
)
def test_fs_growth_and_trend_translation_matches_declared_unit(
    metric: metrics.Metric, raw_metric_name: str
) -> None:
    assert metric.unit == metrics.Unit(metrics.IECNotation("B/d"))

    translation = translation_filesystem_storages_df.translations[raw_metric_name]
    assert isinstance(translation, translations.RenameToAndScaleBy)
    assert translation.metric_name == metric.name
    assert translation.factor == _BYTES_PER_MB
