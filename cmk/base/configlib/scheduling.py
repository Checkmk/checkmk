#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

from cmk.base.configlib.loaded_config import LoadedConfigFragment
from cmk.ccc.hostaddress import HostName
from cmk.utils.labels import LabelManager
from cmk.utils.rulesets.ruleset_matcher import (
    RulesetMatcher,
    SingleServiceRulesetMatcherFirstParsed,
)
from cmk.utils.servicename import ServiceName

SERVICE_CHECK_INTERVAL = 60.0  # seconds


def make_check_interval_config(
    loaded_config: LoadedConfigFragment,
    matcher: RulesetMatcher,
    label_manager: LabelManager,
) -> Callable[[HostName, ServiceName], float]:
    """Create a callback that returns the check interval for a given host in seconds."""
    config = SingleServiceRulesetMatcherFirstParsed(
        host_ruleset=loaded_config.extra_service_conf.get("check_interval", ()),
        default=SERVICE_CHECK_INTERVAL,
        matcher=matcher,
        labels_of_host=label_manager.labels_of_host,
        # Convert to seconds. Crash if this is not a number.
        parser=lambda x: float(x) * 60.0,  # type: ignore[arg-type]
    )

    def get_check_interval(host_name: HostName, service_name: str) -> float:
        return config(
            host_name,
            service_name,
            # note: services with check interval never have discovered labels.
            label_manager.labels_of_service(host_name, service_name, discovered_labels={}),
        )

    return get_check_interval
