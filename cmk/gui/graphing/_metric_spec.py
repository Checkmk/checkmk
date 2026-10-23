#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.gui.i18n import translate_to_current_language


def registered_metric_ids_and_titles(
    registered_metrics: Mapping[str, metrics_v1.Metric],
) -> Iterator[tuple[str, str]]:
    for metric_id, metric in registered_metrics.items():
        yield metric_id, metric.title.localize(translate_to_current_language)
