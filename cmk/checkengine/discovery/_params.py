#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import dataclasses
import itertools
from collections.abc import Callable, Sequence
from typing import Literal

from cmk.utils.check_utils import ParametersTypeAlias
from cmk.utils.hostaddress import HostName
from cmk.utils.rulesets import RuleSetName
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher, RuleSpec

from cmk.checkengine.parameters import Parameters

from ._filters import RediscoveryParameters


@dataclasses.dataclass(frozen=True)
class DiscoveryCheckParameters:
    commandline_only: bool
    check_interval: int
    severity_new_services: int
    severity_vanished_services: int
    severity_changed_service_labels: int
    severity_changed_service_params: int
    severity_new_host_labels: int
    rediscovery: RediscoveryParameters


def get_plugin_parameters(
    host_name: HostName,
    matcher: RulesetMatcher,
    *,
    default_parameters: ParametersTypeAlias | None,
    ruleset_name: RuleSetName | None,
    ruleset_type: Literal["all", "merged"],
    rules_getter_function: Callable[[RuleSetName], Sequence[RuleSpec]],
) -> None | Parameters | list[Parameters]:
    if default_parameters is None:
        # This means the function will not accept any params.
        return None
    if ruleset_name is None:
        # This means we have default params, but no rule set.
        # Not very sensical for discovery functions, but not forbidden by the API either.
        return Parameters(default_parameters)

    rules = rules_getter_function(ruleset_name)

    if ruleset_type == "all":
        host_rules = matcher.get_host_values(host_name, rules)
        return [Parameters(d) for d in itertools.chain(host_rules, (default_parameters,))]

    if ruleset_type == "merged":
        return Parameters(
            {
                **default_parameters,
                **matcher.get_host_merged_dict(host_name, rules),
            }
        )

    # validation should have prevented this
    raise NotImplementedError(f"unknown discovery rule set type {ruleset_type!r}")
