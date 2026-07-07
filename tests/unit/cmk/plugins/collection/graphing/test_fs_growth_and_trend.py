#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import metrics, translations
from cmk.graphing.v1.translations import Translation
from cmk.plugins.collection.graphing.fs_growth_and_trend import metric_fs_growth, metric_fs_trend
from cmk.plugins.collection.graphing.mem_growth import metric_mem_growth
from cmk.plugins.collection.graphing.mem_trend import metric_mem_trend
from cmk.plugins.collection.graphing.translations import (
    translation_cisco_mem_cisco_mem_asa_cisco_mem_asa64,
    translation_filesystem_storages_df,
)

# NOTE (2.5.0 backport): the proxmox_ve node-storages translation lives in the separate
# cmk-plugins package, which is not importable from this test target on 2.5.0. Its
# growth/trend scaling is guarded by
# tests/plugins_siteless/plugins_consistency/test_graphing_plugins.py, which loads every
# graphing plugin (including proxmox_ve) and asserts the same MB/day -> bytes/day factor.

# The df/mem checks emit growth/trend in MB/day (packages/cmk-plugins/cmk/plugins/lib/size_trend.py).
_BYTES_PER_MB = 1048576


@pytest.mark.parametrize(
    "translation, raw_metric_name, metric",
    [
        pytest.param(
            translation_filesystem_storages_df, "growth", metric_fs_growth, id="df-growth"
        ),
        pytest.param(translation_filesystem_storages_df, "trend", metric_fs_trend, id="df-trend"),
        pytest.param(
            translation_cisco_mem_cisco_mem_asa_cisco_mem_asa64,
            "growth",
            metric_mem_growth,
            id="cisco-mem-growth",
        ),
        pytest.param(
            translation_cisco_mem_cisco_mem_asa_cisco_mem_asa64,
            "trend",
            metric_mem_trend,
            id="cisco-mem-trend",
        ),
    ],
)
def test_growth_and_trend_translation_matches_declared_unit(
    translation: Translation, raw_metric_name: str, metric: metrics.Metric
) -> None:
    assert metric.unit == metrics.Unit(metrics.IECNotation("B/d"))

    rename = translation.translations[raw_metric_name]
    assert isinstance(rename, translations.RenameToAndScaleBy)
    assert rename.metric_name == metric.name
    assert rename.factor == _BYTES_PER_MB
