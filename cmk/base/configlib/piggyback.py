#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Iterable

from cmk.ccc.hostaddress import HostName
from cmk.piggyback.backend import parse_flattened_piggyback_time_settings, PiggybackTimeSettings
from cmk.utils.labels import Labels
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher

from .loaded_config import LoadedConfigFragment


def make_piggyback_time_settings(
    loaded_config: LoadedConfigFragment,
    matcher: RulesetMatcher,
    labels_of_host: Callable[[HostName], Labels],
    source_host_names: Iterable[HostName],
) -> PiggybackTimeSettings:
    return [
        setting
        for source_host_name in source_host_names
        for rule in matcher.get_host_values_all(
            source_host_name, loaded_config.piggybacked_host_files, labels_of_host
        )[:1]  # first match rule
        for setting in parse_flattened_piggyback_time_settings(source_host_name, rule)
    ]
