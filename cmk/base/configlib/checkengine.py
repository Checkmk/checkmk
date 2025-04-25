#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import dataclasses
from collections.abc import Callable, Container, Mapping, Sequence
from typing import (
    assert_never,
)

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName

from cmk.utils.labels import Labels
from cmk.utils.rulesets import RuleSetName
from cmk.utils.rulesets.ruleset_matcher import (
    RulesetMatcher,
    RulesetName,
    RuleSpec,
)
from cmk.utils.servicename import Item

from cmk.checkengine.checking import (
    ABCCheckingConfig,
)
from cmk.checkengine.discovery import (
    ABCDiscoveryConfig,
)
from cmk.checkengine.plugins import (
    RuleSetTypeName,
)


class CheckingConfig(ABCCheckingConfig):
    def __init__(
        self,
        matcher: RulesetMatcher,
        labels_of_host: Callable[[HostName], Labels],
        parameter_rules: Mapping[str, Sequence[RuleSpec[Mapping[str, object]]]],
        service_rule_names: Container[str],
    ) -> None:
        self._matcher = matcher
        self._parameter_rules = parameter_rules
        self._labels_of_host = labels_of_host
        self._service_rule_names = service_rule_names

    def __call__(
        self, host_name: HostName, item: Item, service_labels: Labels, ruleset_name: RulesetName
    ) -> Sequence[Mapping[str, object]]:
        rules = self._parameter_rules.get(ruleset_name)
        if not rules:
            return []

        try:
            if item is None and ruleset_name not in self._service_rule_names:
                return self._matcher.get_host_values(host_name, rules, self._labels_of_host)

            # checks with an item need service-specific rules
            return self._matcher.get_checkgroup_ruleset_values(
                host_name, item, service_labels, rules, self._labels_of_host
            )
        except MKGeneralException as e:
            raise MKGeneralException(f"{e} (on host {host_name}, checkgroup {ruleset_name})")


@dataclasses.dataclass(frozen=True)
class DiscoveryConfig(ABCDiscoveryConfig):
    """Implementation of the discovery configuration"""

    matcher: RulesetMatcher
    labels_of_host: Callable[[HostName], Labels]
    rules: Mapping[RuleSetName, Sequence[RuleSpec[Mapping[str, object]]]]

    def __call__(
        self, host_name: HostName, rule_set_name: RuleSetName, rule_set_type: RuleSetTypeName
    ) -> Mapping[str, object] | Sequence[Mapping[str, object]]:
        rule = self.rules.get(rule_set_name, [])
        if rule_set_type == "merged":
            return self.matcher.get_host_merged_dict(host_name, rule, self.labels_of_host)
        if rule_set_type == "all":
            return self.matcher.get_host_values(host_name, rule, self.labels_of_host)
        assert_never(rule_set_type)
