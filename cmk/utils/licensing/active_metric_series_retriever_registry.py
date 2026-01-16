#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

from cmk.ccc.version import Edition, edition
from cmk.utils import paths
from cmk.utils.licensing.helper import init_logging

logger = init_logging()


class ActiveMetricSeriesRetrieverRegistry:
    def __init__(self) -> None:
        self.metric_series_retriever_function: Callable[[], int | None] | None = None

    def register(self, metric_series_retriever_function: Callable[[], int | None]) -> None:
        self.metric_series_retriever_function = metric_series_retriever_function


active_metric_series_retriever_registry = ActiveMetricSeriesRetrieverRegistry()


def get_num_active_metric_series() -> int | None:
    if active_metric_series_retriever_registry.metric_series_retriever_function is not None:
        try:
            return active_metric_series_retriever_registry.metric_series_retriever_function()
        except Exception as e:
            logger.error(
                "Error when retrieving the active metric series count (%s): %s", type(e).__name__, e
            )
    elif edition(paths.omd_root) in [Edition.ULTIMATE, Edition.ULTIMATEMT, Edition.CLOUD]:
        logger.error("There is no registered active metric series function, while it should")
    return None
