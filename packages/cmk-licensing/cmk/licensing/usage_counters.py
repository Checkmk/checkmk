#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Collection of feature-specific license usage counters.

Features that contribute counters to the license usage sample expose a
``license_usage_counter_*`` plug-in from ``cmk/plugins/<family>/licensing/``.
The plug-in file only ships in editions shipping the feature, which is what
makes the discovery edition-agnostic: no explicit edition check is required.
"""

import logging
from collections.abc import Iterable, Mapping, Sequence

from cmk.licensing.internal import (
    CounterCollectionContext,
    LicenseUsageCounter,
    LicenseUsageCounterName,
)
from cmk.licensing.plugin_loader import discover_licensing_plugins


def discover_license_usage_counter_plugins() -> Sequence[LicenseUsageCounter]:
    return list(discover_licensing_plugins(raise_errors=True).plugins.values())


def collect_license_usage_counters(
    plugins: Iterable[LicenseUsageCounter],
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
