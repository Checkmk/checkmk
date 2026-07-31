#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Discovery and collection of feature-specific license usage counters.

Features that contribute counters to the license usage sample expose a
``license_usage_counter_*`` plug-in from a well-known module of their package.
The module only exists in editions shipping the feature, which is what makes
the discovery edition-agnostic: no explicit edition check is required.
"""

import logging
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cmk.livestatus_client as livestatus
from cmk.discover_plugins import discover_plugins_from_modules

LICENSE_LABEL_NAME = "cmk/licensing"
LICENSE_LABEL_EXCLUDE = "excluded"

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
    omd_root: Path
    query_livestatus: Callable[[str], Sequence[Sequence[livestatus.LivestatusColumn]]]


@dataclass(frozen=True)
class LicenseUsageCounterPlugin:
    """A discoverable provider of feature-specific license usage counters.

    ``collect`` returns a mapping of counter names to values which end up in
    the license usage sample.
    """

    name: str
    collect: Callable[[CounterCollectionContext], Mapping[LicenseUsageCounterName, int]]


def discover_license_usage_counter_plugins() -> Sequence[LicenseUsageCounterPlugin]:
    return list(
        discover_plugins_from_modules(
            {LicenseUsageCounterPlugin: "license_usage_counter_"},
            # Modules that may expose a `LicenseUsageCounterPlugin`. Passed
            # unconditionally: modules absent from the running edition are
            # simply skipped.
            (
                "cmk.metric_backend.license_usage",  # non-free, ships with the metric backend
                "cmk.robotmk.license_usage",  # non-free, ships with synthetic monitoring
            ),
            skip_wrong_types=False,
            raise_errors=True,
        ).plugins.values()
    )


def collect_license_usage_counters(
    plugins: Iterable[LicenseUsageCounterPlugin],
    context: CounterCollectionContext,
    logger: logging.Logger,
) -> Mapping[LicenseUsageCounterName, int]:
    """Collect the counters of all given plug-ins.

    A failing plug-in is logged and skipped so that it cannot break the
    license usage sample as a whole.
    """
    counters: dict[LicenseUsageCounterName, int] = {}
    for plugin in plugins:
        try:
            plugin_counters = plugin.collect(context)
        except Exception:
            logger.exception(
                "Error when collecting the license usage counters of %(name)s",
                {"name": plugin.name},
            )
            continue
        for counter_name, value in plugin_counters.items():
            if counter_name in counters:
                logger.error(
                    "License usage counter %(counter_name)s of %(name)s already collected",
                    {"counter_name": counter_name, "name": plugin.name},
                )
                continue
            counters[counter_name] = value
    return counters
