#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Provides functionality to measure how effective the ruleset matching currently is"""

import dataclasses
import json
import os
import time
from collections.abc import Mapping
from typing import Any, Sequence

from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.paths import omd_root
from cmk.utils.servicename import Item, ServiceName


@dataclasses.dataclass(kw_only=True)
class AllHostsMatchingStats:
    condition_hit: dict[str, int] = dataclasses.field(default_factory=dict)
    condition_miss: dict[str, int] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(kw_only=True)
class FunctionCallStats:
    with_results: int = 0
    without_results: int = 0


@dataclasses.dataclass(kw_only=True)
class ServiceRulesetFunctionCallStats(FunctionCallStats):
    hosts_without_results: set[HostName] = dataclasses.field(default_factory=set)
    services_descr_without_results: set[str] = dataclasses.field(default_factory=set)


@dataclasses.dataclass(kw_only=True)
class MatchingStats:
    ruleset_calls: FunctionCallStats = dataclasses.field(default_factory=FunctionCallStats)
    all_matching_hosts_stats: AllHostsMatchingStats = dataclasses.field(
        default_factory=AllHostsMatchingStats
    )
    hosts_per_rule: list[tuple[str, list[HostName]]] = dataclasses.field(default_factory=list)
    matched_rules_per_host: dict[HostName, set[str]] = dataclasses.field(default_factory=dict)
    # For host rulesets, there are probably no unused computed hosts
    # Unless some mechanic asks only for one specific host.
    unused_computed_hosts_per_rule: dict[str, set[HostName]] = dataclasses.field(
        default_factory=dict
    )

    def track_host_ruleset_call(self, host_results: Sequence[object]) -> None:
        if len(host_results) > 0:
            self.ruleset_calls.with_results += 1
        else:
            self.ruleset_calls.without_results += 1

    def track_unnecessarily_computed_hosts(self, hostname: HostName) -> None:
        for rule_hosts in self.unused_computed_hosts_per_rule.values():
            rule_hosts.discard(hostname)

    def serialize(self) -> dict[str, Any]:
        return {
            "ruleset_calls": dataclasses.asdict(self.ruleset_calls),
            "all_matching_hosts_stats": dataclasses.asdict(self.all_matching_hosts_stats),
            "hosts_per_rule": self.hosts_per_rule,
            "unused_computed_hosts_per_rule": {
                x: list(y) for x, y in self.unused_computed_hosts_per_rule.items() if y
            },
        }


@dataclasses.dataclass(kw_only=True)
class HostRulesetMatchingStats(MatchingStats):
    def serialize(self) -> dict[str, Any]:
        base_serialize = super().serialize()
        base_serialize.update(
            {
                "type": "host_rule",
            }
        )
        return base_serialize


@dataclasses.dataclass(kw_only=True)
class ServiceRulesetMatchingStats(MatchingStats):
    matched_rules_per_service: dict[str, set[str]] = dataclasses.field(default_factory=dict)

    service_matching_attempts: ServiceRulesetFunctionCallStats = dataclasses.field(
        default_factory=lambda: ServiceRulesetFunctionCallStats(
            hosts_without_results=set(),
            services_descr_without_results=set(),
        )
    )

    def track_service_ruleset_call(
        self,
        never_matched: bool,
        match_object_host: HostName | HostAddress,
        match_object_service: ServiceName | Item | None = None,
    ) -> None:
        if never_matched:
            self.ruleset_calls.without_results += 1
            self.service_matching_attempts.hosts_without_results.add(match_object_host)
            if match_object_service is not None:
                self.service_matching_attempts.services_descr_without_results.add(
                    match_object_service
                )
        else:
            self.ruleset_calls.with_results += 1

    def serialize(self) -> dict[str, Any]:
        base_serialized = super().serialize()
        base_serialized.update(
            {
                "type": "service_rule",
                "used_rules_per_service": {
                    key: list(value) for key, value in self.matched_rules_per_service.items()
                },
                "service_rulesets": {
                    "hosts_without_results": list(
                        self.service_matching_attempts.hosts_without_results
                    ),
                    "services_descr_without_results": list(
                        self.service_matching_attempts.services_descr_without_results
                    ),
                },
            }
        )
        return base_serialized


def persist_matching_stats(
    matching_stats: dict[int, HostRulesetMatchingStats | ServiceRulesetMatchingStats],
    base_dir: str,
    ruleset_id_name_mapping: Mapping[int, str],
    separate_files: bool = False,
) -> None:
    if os.getcwd().removeprefix("/opt") != str(omd_root):
        return

    os.makedirs(base_dir, exist_ok=True)
    single_file_name = "ruleset_matching_stats"
    filepath = f"{base_dir.rstrip('/')}/{time.time() if separate_files else single_file_name}.json"

    serialized = {key: value.serialize() for key, value in matching_stats.items()}
    serialized_with_names = {
        ruleset_id_name_mapping.get(key, key): values for key, values in serialized.items()
    }

    with open(filepath, "w") as stats_file:
        json.dump(serialized_with_names, stats_file, indent=4)
