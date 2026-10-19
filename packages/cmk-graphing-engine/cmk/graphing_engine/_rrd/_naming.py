#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from dataclasses import dataclass
from typing import NewType

from cmk.graphing_engine._data._naming import MetricName

HostName = NewType("HostName", str)
ServiceName = NewType("ServiceName", str)
SiteID = NewType("SiteID", str)


def rrd_metric_name(text: str) -> MetricName:
    return MetricName(
        text.replace(" ", "_")
        .replace(":", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace("\x00", "_")
    )


@dataclass(frozen=True, kw_only=True)
class Service:
    # The monitoring site the service lives on, when known. Carried through matching so the metrics
    # built for the service can be tagged with it; None means "site not (yet) known".
    site_id: SiteID | None = None
    host_name: HostName
    service_name: ServiceName


class PredictPrefix(enum.StrEnum):
    LOWER = "predict_lower_"
    UPPER = "predict_"


def split_predict_prefix(metric_name: str) -> tuple[str, str]:
    for prefix in PredictPrefix:
        if metric_name.startswith(prefix):
            return prefix, metric_name[len(prefix) :]
    return "", metric_name
