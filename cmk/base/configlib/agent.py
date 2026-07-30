#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

from cmk.base.configlib.loaded_config import BaseConfig
from cmk.ccc.hostaddress import HostName
from cmk.ruleset_matcher.labels import LabelManager
from cmk.ruleset_matcher.matcher import RulesetMatcher


def make_only_from_config(
    loaded_config: BaseConfig,
    matcher: RulesetMatcher,
    label_manager: LabelManager,
) -> Callable[[HostName], None | list[str] | str]:
    """Create a callback returning the IPs a host's agent may be accessed from."""

    def only_from(host_name: HostName) -> None | list[str] | str:
        """The agent of a host may be configured to be accessible only from specific IPs"""
        ruleset = loaded_config.agent_config.get("only_from", [])
        if not ruleset:
            return None

        entries = matcher.get_host_values_all(host_name, ruleset, label_manager.labels_of_host)
        return entries[0] if entries else None

    return only_from
