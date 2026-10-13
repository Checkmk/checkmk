#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Name of the host or service label marking an entity as excluded from
# licensing, and the label value that does so.
LICENSE_LABEL_NAME = "cmk/licensing"
LICENSE_LABEL_EXCLUDE = "excluded"

# TODO: this should not be part of the API. It holds plug-in specific information.
# The counter names plug-ins may emit. Every name corresponds to a field of
# the license usage sample which create_sample() fills from the collected
# counters; sharing this type makes mypy check both sides of that contract.
LicenseUsageCounterName = Literal[
    "synthetic_tests",
    "synthetic_tests_excluded",
    "synthetic_kpis",
    "synthetic_kpis_excluded",
    "active_metric_series",
]


@dataclass(frozen=True)
class CounterCollectionContext:
    """What a counter plug-in may use to compute its counters."""

    omd_root: Path
    query_livestatus: Callable[[str], Sequence[Sequence[object]]]


@dataclass(frozen=True)
class LicenseUsageCounter:
    """A discoverable provider of feature-specific license usage counters.

    ``collect`` returns a mapping of counter names to values which end up in
    the license usage sample.
    """

    name: str
    collect: Callable[[CounterCollectionContext], Mapping[LicenseUsageCounterName, int]]
