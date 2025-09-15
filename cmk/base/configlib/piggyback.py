#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Iterable

from cmk.ccc.hostaddress import HostName
from cmk.piggyback.backend import (
    get_current_piggyback_sources_of_host,
    parse_flattened_piggyback_time_settings,
    PiggybackTimeSettings,
)
from cmk.utils.labels import Labels
from cmk.utils.paths import omd_root
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher

from .loaded_config import LoadedConfigFragment


def guess_piggybacked_hosts_time_settings(
    loaded_config: LoadedConfigFragment,
    matcher: RulesetMatcher,
    labels_of_host: Callable[[HostName], Labels],
    piggybacked_hostname: HostName,
) -> PiggybackTimeSettings:
    # NOTE: piggyback time settings are configured in rules matching on the source hosts,
    # but applied when dealing with the destination hosts (aka piggybacked hosts) in the
    # fetcher and the summarizer.
    # This *guesses* which rulesets are relevant, by matching on the hosts that *currently*
    # provide piggyback data for the given piggybacked host.
    # For the fetcher, this function is evaluated at config creation time, so this might
    # well be wrong.
    return make_piggyback_time_settings(
        loaded_config,
        matcher,
        labels_of_host,
        source_host_names=sorted(
            get_current_piggyback_sources_of_host(omd_root, piggybacked_hostname)
        ),
    )


def make_piggyback_time_settings(
    loaded_config: LoadedConfigFragment,
    matcher: RulesetMatcher,
    labels_of_host: Callable[[HostName], Labels],
    source_host_names: Iterable[HostName],
) -> PiggybackTimeSettings:
    return [
        *(
            setting
            for source_host_name in source_host_names
            for rule in matcher.get_host_values_all(
                source_host_name, loaded_config.piggybacked_host_files, labels_of_host
            )[:1]  # first match rule
            for setting in parse_flattened_piggyback_time_settings(source_host_name, rule)
        ),
        (None, "max_cache_age", loaded_config.piggyback_max_cachefile_age),
    ]
