#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import NewType

MetricName = NewType("MetricName", str)
HostName = NewType("HostName", str)
ServiceName = NewType("ServiceName", str)
SiteID = NewType("SiteID", str)


@dataclass(frozen=True, kw_only=True)
class Service:
    site_id: SiteID | None = None
    host_name: HostName
    service_name: ServiceName
