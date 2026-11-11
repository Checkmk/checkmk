#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.utils.rulesets.ruleset_matcher import (
    RuleConditionsSpec,
    RulesetMatcher,
    RuleSpec,
    SingleHostMatcher,
)
from cmk.utils.tags import TagGroupID, TagID

HOST, OTHER = HostName("host"), HostName("other")
HOST_TAGS = {
    HOST: {TagGroupID("criticality"): TagID("prod"), TagGroupID("agent"): TagID("cmk-agent")},
    OTHER: {TagGroupID("criticality"): TagID("test"), TagGroupID("agent"): TagID("cmk-agent")},
}
HOST_PATHS = {HOST: "/wato/linux/hosts.mk", OTHER: "/wato/windows/hosts.mk"}
HOST_LABELS = {HOST: {"os": "linux"}, OTHER: {"os": "windows"}}

# fmt: off
CONDITIONS: Sequence[tuple[str, RuleConditionsSpec, bool]] = [
    ("no conditions", {}, True),
    ("folder of the host", {"host_folder": "/wato/linux/"}, True),
    ("other folder", {"host_folder": "/wato/windows/"}, False),
    ("tag of the host", {"host_tags": {TagGroupID("criticality"): TagID("prod")}}, True),
    ("other tag", {"host_tags": {TagGroupID("criticality"): TagID("test")}}, False),
    ("negated other tag", {"host_tags": {TagGroupID("criticality"): {"$ne": TagID("test")}}}, True),
    ("one of the tags", {"host_tags": {TagGroupID("criticality"): {"$or": [TagID("test"), TagID("prod")]}}}, True),
    ("none of the tags", {"host_tags": {TagGroupID("criticality"): {"$nor": [TagID("prod")]}}}, False),
    ("explicit host", {"host_name": ["host"]}, True),
    ("other explicit host", {"host_name": ["other"]}, False),
    ("empty host list", {"host_name": []}, False),
    ("host regex", {"host_name": [{"$regex": "ho.*"}]}, True),
    ("negated other host", {"host_name": {"$nor": ["other"]}}, True),
    ("label of the host", {"host_label_groups": [("and", [("and", "os:linux")])]}, True),
    ("other label", {"host_label_groups": [("and", [("and", "os:windows")])]}, False),
    ("tag of the host but other host", {"host_tags": {TagGroupID("criticality"): TagID("prod")}, "host_name": ["other"]}, False),
]
# fmt: on


def _rule(rule_id: str, condition: RuleConditionsSpec) -> RuleSpec[str]:
    return {"id": rule_id, "value": rule_id, "condition": condition}


def _single_host_matcher() -> SingleHostMatcher:
    return SingleHostMatcher(HOST, HOST_TAGS[HOST], HOST_PATHS[HOST], HOST_LABELS[HOST])


def _ruleset_matcher() -> RulesetMatcher:
    return RulesetMatcher(
        host_tags=HOST_TAGS,
        host_paths=HOST_PATHS,
        all_configured_hosts=frozenset(HOST_TAGS),
        clusters_of={},
        nodes_of={},
    )


@pytest.mark.parametrize(
    ("condition", "expected"),
    [pytest.param(condition, expected, id=name) for name, condition, expected in CONDITIONS],
)
def test_single_host_matcher_evaluates_the_condition_for_the_host(
    condition: RuleConditionsSpec, expected: bool
) -> None:
    assert _single_host_matcher().matches(_rule("rule", condition)) is expected


def test_single_host_matcher_skips_disabled_rules() -> None:
    rule: RuleSpec[str] = {
        "id": "rule",
        "value": "rule",
        "condition": {},
        "options": {"disabled": True},
    }

    assert _single_host_matcher().matches(rule) is False


def test_matching_rule_ids_keep_the_order_of_the_ruleset() -> None:
    ruleset = [
        _rule("first", {}),
        _rule("not matching", {"host_name": ["other"]}),
        _rule("last", {}),
    ]

    assert _single_host_matcher().matching_rule_ids(ruleset) == ["first", "last"]


def test_empty_host_list_matches_nothing_after_a_rule_without_host_condition() -> None:
    ruleset = [_rule("every host", {}), _rule("no host", {"host_name": []})]
    ruleset_matcher = _ruleset_matcher()

    assert list(ruleset_matcher.get_host_values_all(HOST, ruleset, HOST_LABELS.__getitem__)) == [
        "every host"
    ]


@pytest.mark.parametrize(
    ("condition", "expected"),
    [pytest.param(condition, expected, id=name) for name, condition, expected in CONDITIONS],
)
def test_get_matching_hosts_holds_the_host_iff_the_condition_matches_it(
    condition: RuleConditionsSpec, expected: bool
) -> None:
    matching_hosts = _ruleset_matcher().get_matching_hosts(
        _rule("rule", condition), HOST_LABELS.__getitem__
    )

    assert (HOST in matching_hosts) is expected


def test_get_matching_hosts_of_a_disabled_rule_is_empty() -> None:
    rule: RuleSpec[str] = {
        "id": "rule",
        "value": "rule",
        "condition": {},
        "options": {"disabled": True},
    }

    assert not _ruleset_matcher().get_matching_hosts(rule, HOST_LABELS.__getitem__)


def test_single_host_matcher_agrees_with_the_ruleset_matcher() -> None:
    ruleset = [_rule(name, condition) for name, condition, _expected in CONDITIONS]
    ruleset_matcher = _ruleset_matcher()

    ruleset_matcher.ruleset_optimizer.set_all_processed_hosts({HOST})
    matched_by_ruleset_matcher = ruleset_matcher.get_host_values_all(
        HOST, ruleset, HOST_LABELS.__getitem__
    )

    assert _single_host_matcher().matching_rule_ids(ruleset) == list(matched_by_ruleset_matcher)
