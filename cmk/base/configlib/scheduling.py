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
from cmk.utils.timeperiod import TimeperiodName

SERVICE_CHECK_PERIOD = "24X7"

SERVICE_CHECK_INTERVAL = 60.0  # seconds
SERVICE_RETRY_INTERVAL = 60.0  # seconds

MAX_CHECK_ATTEMPTS = 1


def make_check_period_config(
    loaded_config: LoadedConfigFragment,
    matcher: RulesetMatcher,
    label_manager: LabelManager,
) -> Callable[[HostName, ServiceName], TimeperiodName]:
    """Create a callback that returns the check period for a given host/service in seconds."""
    config = SingleServiceRulesetMatcherFirstParsed(
        host_ruleset=loaded_config.extra_service_conf.get("check_period", ()),
        default=SERVICE_CHECK_PERIOD,
        matcher=matcher,
        labels_of_host=label_manager.labels_of_host,
        parser=str,
    )

    def get_check_period(host_name: HostName, service_name: str) -> TimeperiodName:
        return TimeperiodName(
            config(
                host_name,
                service_name,
                # note: services with check periods never have discovered labels.
                label_manager.labels_of_service(host_name, service_name, discovered_labels={}),
            )
        )

    return get_check_period


def make_check_interval_config(
    loaded_config: LoadedConfigFragment,
    matcher: RulesetMatcher,
    label_manager: LabelManager,
) -> Callable[[HostName, ServiceName], float]:
    """Create a callback that returns the check interval for a given host/service in seconds."""
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


def make_retry_interval_config(
    loaded_config: LoadedConfigFragment,
    matcher: RulesetMatcher,
    label_manager: LabelManager,
) -> Callable[[HostName, ServiceName], float]:
    """Create a callback that returns the retry interval for a given host/service in seconds."""
    config = SingleServiceRulesetMatcherFirstParsed(
        host_ruleset=loaded_config.extra_service_conf.get("retry_interval", ()),
        default=SERVICE_RETRY_INTERVAL,
        matcher=matcher,
        labels_of_host=label_manager.labels_of_host,
        # Convert to seconds. Crash if this is not a number.
        parser=lambda x: float(x) * 60.0,  # type: ignore[arg-type]
    )

    def get_retry_interval(host_name: HostName, service_name: ServiceName) -> float:
        return config(
            host_name,
            service_name,
            # note: services with retry interval never have discovered labels.
            label_manager.labels_of_service(host_name, service_name, discovered_labels={}),
        )

    return get_retry_interval


def make_max_check_attempts_config(
    loaded_config: LoadedConfigFragment,
    matcher: RulesetMatcher,
    label_manager: LabelManager,
) -> Callable[[HostName, ServiceName], int]:
    """Create a callback that returns the max check attempts for a given host/service."""
    config = SingleServiceRulesetMatcherFirstParsed(
        host_ruleset=loaded_config.extra_service_conf.get("max_check_attempts", ()),
        default=MAX_CHECK_ATTEMPTS,
        matcher=matcher,
        labels_of_host=label_manager.labels_of_host,
        # Convert to seconds. Crash if this is not a number.
        parser=int,  # type: ignore[arg-type]
    )

    def get_retry_interval(host_name: HostName, service_name: ServiceName) -> int:
        return config(
            host_name,
            service_name,
            label_manager.labels_of_service(host_name, service_name, discovered_labels={}),
        )

    return get_retry_interval
