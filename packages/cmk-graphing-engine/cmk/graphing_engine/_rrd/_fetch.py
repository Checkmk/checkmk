#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Protocol

from cmk.graphing_engine._data._naming import MetricName

from ._naming import Service


class FetchMetricNamesProtocol(Protocol):
    def __call__(self) -> Mapping[Service, frozenset[MetricName]]: ...
