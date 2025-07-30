#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable

from cmk.base.configlib.loaded_config import LoadedConfigFragment
from cmk.ccc.hostaddress import HostName
from cmk.fetchers import TCPFetcherConfig
from cmk.utils.labels import Labels
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher, SingleHostRulesetMatcherFirst


def make_tcp_fetcher_config(
    loaded_config: LoadedConfigFragment,
    ruleset_matcher: RulesetMatcher,
    labels_of_host: Callable[[HostName], Labels],
) -> TCPFetcherConfig:
    return TCPFetcherConfig(
        agent_port=SingleHostRulesetMatcherFirst(
            loaded_config.agent_ports,
            loaded_config.agent_port,
            ruleset_matcher,
            labels_of_host,
        ),
        connect_timeout=SingleHostRulesetMatcherFirst(
            loaded_config.tcp_connect_timeouts,
            loaded_config.tcp_connect_timeout,
            ruleset_matcher,
            labels_of_host,
        ),
        encryption_handling=SingleHostRulesetMatcherFirst(
            loaded_config.encryption_handling,
            None,
            ruleset_matcher,
            labels_of_host,
        ),
        symmetric_agent_encryption=SingleHostRulesetMatcherFirst(
            loaded_config.agent_encryption,
            None,
            ruleset_matcher,
            labels_of_host,
        ),
    )
