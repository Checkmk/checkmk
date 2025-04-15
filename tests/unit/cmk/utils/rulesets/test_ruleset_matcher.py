#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from pytest import MonkeyPatch

from tests.testlib.base import Scenario

from cmk.utils.hostaddress import HostName
from cmk.utils.rulesets.ruleset_matcher import (
    LabelManager,
    matches_tag_condition,
    RuleConditionsSpec,
    RulesetMatcher,
    RulesetMatchObject,
    RuleSpec,
    TagCondition,
)
from cmk.utils.servicename import ServiceName
from cmk.utils.tags import TagConfig, TagGroupID, TagID

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.discovery import AutocheckEntry


def test_ruleset_match_object_host_name() -> None:
    obj = RulesetMatchObject(host_name=HostName("abc"), service_description=None)
    assert obj.host_name == "abc"


ruleset: Sequence[RuleSpec[str]] = [
    {
        "id": "1",
        "value": "BLA",
        "condition": {
            "host_name": ["host1"],
        },
        "options": {},
    },
    {
        "id": "2",
        "value": "BLUB",
        "condition": {"host_name": ["host1", "host2"]},
        "options": {},
    },
    {
        "id": "3",
        "value": "BLA",
        "condition": {
            "host_name": ["xyz"],
        },
        "options": {
            "disabled": True,
        },
    },
    {
        "id": "4",
        "value": "LEVEL1",
        "condition": {"host_folder": "/lvl1/"},
    },
    {
        "id": "5",
        "value": "LEVEL2",
        "condition": {"host_folder": "/lvl1/lvl2/"},
    },
    {
        "id": "6",
        "value": "XYZ",
        "condition": {
            "host_name": [],
        },
        "options": {},
    },
]

host_label_ruleset: Sequence[RuleSpec[str]] = [
    # test simple label match
    {
        "id": "id0",
        "value": "os_linux",
        "condition": {
            "host_label_groups": [("and", [("and", "os:linux")])],
        },
        "options": {},
    },
    # test implicit AND and unicode value match
    {
        "id": "id2",
        "value": "abc",
        "condition": {
            "host_label_groups": [
                (
                    "and",
                    [
                        ("and", "os:linux"),
                        ("and", "abc:xä"),
                    ],
                )
            ],
        },
        "options": {},
    },
    # test negation of label
    {
        "id": "id3",
        "value": "hu",
        "condition": {
            "host_label_groups": [("and", [("not", "hu:ha")])],
        },
        "options": {},
    },
    # test unconditional match
    {
        "id": "id4",
        "value": "BLA",
        "condition": {},
        "options": {},
    },
]


@pytest.mark.parametrize(
    "hostname, expected_result",
    [
        (HostName("host1"), ["os_linux", "abc", "BLA"]),
        (HostName("host2"), ["hu", "BLA"]),
    ],
)
def test_ruleset_matcher_get_host_values_labels(
    hostname: HostName, expected_result: Sequence[str]
) -> None:
    matcher = RulesetMatcher(
        host_tags={HostName("host1"): {}, HostName("host2"): {}},
        host_paths={},
        label_manager=LabelManager(
            explicit_host_labels={
                HostName("host1"): {"os": "linux", "abc": "xä", "hu": "ha"},
                HostName("host2"): {},
            },
            host_label_rules=(),
            service_label_rules=(),
            discovered_labels_of_service=lambda *args, **kw: {},
            builtin_host_labels={},
        ),
        all_configured_hosts=frozenset([HostName("host1"), HostName("host2")]),
        clusters_of={},
        nodes_of={},
    )

    assert list(matcher.get_host_values(hostname, ruleset=host_label_ruleset)) == expected_result


def test_labels_of_service(monkeypatch: MonkeyPatch) -> None:
    test_host = HostName("test-host")
    xyz_host = HostName("xyz")
    ruleset_matcher = RulesetMatcher(
        host_tags={test_host: {TagGroupID("agent"): TagID("no-agent")}, xyz_host: {}},
        host_paths={},
        label_manager=LabelManager(
            explicit_host_labels={},
            host_label_rules=(),
            service_label_rules=[
                {
                    "condition": {
                        "service_description": [{"$regex": "CPU load$"}],
                        "host_tags": {TagGroupID("agent"): TagID("no-agent")},
                    },
                    "id": "01",
                    "value": {"label1": "val1"},
                },
                {
                    "condition": {
                        "service_description": [{"$regex": "CPU load$"}],
                        "host_tags": {TagGroupID("agent"): TagID("no-agent")},
                    },
                    "id": "02",
                    "value": {"label2": "val2"},
                },
            ],
            discovered_labels_of_service=lambda *args, **kw: {},
            builtin_host_labels={},
        ),
        all_configured_hosts=frozenset([test_host, xyz_host]),
        clusters_of={},
        nodes_of={},
    )

    assert not ruleset_matcher.labels_of_service(xyz_host, "CPU load")
    assert not ruleset_matcher.label_sources_of_service(xyz_host, "CPU load")

    assert ruleset_matcher.labels_of_service(test_host, "CPU load") == {
        "label1": "val1",
        "label2": "val2",
    }
    assert ruleset_matcher.label_sources_of_service(test_host, "CPU load") == {
        "label1": "ruleset",
        "label2": "ruleset",
    }


def test_labels_of_service_discovered_labels() -> None:
    test_host = HostName("test-host")
    xyz_host = HostName("xyz")
    ruleset_matcher = RulesetMatcher(
        host_tags={test_host: {}},
        host_paths={},
        label_manager=LabelManager(
            explicit_host_labels={},
            host_label_rules=(),
            service_label_rules=(),
            discovered_labels_of_service=(
                lambda host_name, *args, **kw: {"äzzzz": "eeeeez"} if host_name == test_host else {}
            ),
            builtin_host_labels={},
        ),
        all_configured_hosts=frozenset([test_host]),
        clusters_of={},
        nodes_of={},
    )

    service_description = "CPU load"

    assert not ruleset_matcher.labels_of_service(xyz_host, "CPU load")
    assert not ruleset_matcher.label_sources_of_service(xyz_host, "CPU load")

    assert ruleset_matcher.labels_of_service(test_host, service_description) == {"äzzzz": "eeeeez"}
    assert ruleset_matcher.label_sources_of_service(test_host, service_description) == {
        "äzzzz": "discovered"
    }


def test_basic_get_host_values() -> None:
    matcher = RulesetMatcher(
        host_tags={
            HostName("abc"): {},
            HostName("xyz"): {},
            HostName("host1"): {},
            HostName("host2"): {},
        },
        host_paths={},
        label_manager=LabelManager(
            explicit_host_labels={},
            host_label_rules=(),
            service_label_rules=(),
            discovered_labels_of_service=lambda *args, **kw: {},
            builtin_host_labels={},
        ),
        all_configured_hosts=frozenset(
            [
                HostName("abc"),
                HostName("xyz"),
                HostName("host1"),
                HostName("host2"),
            ]
        ),
        clusters_of={},
        nodes_of={},
    )

    assert not list(matcher.get_host_values(HostName("abc"), ruleset=ruleset))
    assert not list(matcher.get_host_values(HostName("xyz"), ruleset=ruleset))
    assert list(matcher.get_host_values(HostName("host1"), ruleset=ruleset)) == [
        "BLA",
        "BLUB",
    ]
    assert list(matcher.get_host_values(HostName("host2"), ruleset=ruleset)) == ["BLUB"]


def test_basic_get_host_values_subfolders() -> None:
    matcher = RulesetMatcher(
        host_tags={
            HostName("abc"): {},
            HostName("xyz"): {},
            HostName("lvl1"): {},
            HostName("lvl2"): {},
            HostName("lvl1a"): {},
        },
        host_paths={
            HostName("lvl1"): "/lvl1/hosts.mk",
            HostName("lvl2"): "/lvl1/lvl2/hosts.mk",
            HostName("lvl1a"): "/lvl1_a/hosts.mk",
        },
        label_manager=LabelManager(
            explicit_host_labels={},
            host_label_rules=(),
            service_label_rules=(),
            discovered_labels_of_service=lambda *args, **kw: {},
            builtin_host_labels={},
        ),
        all_configured_hosts=frozenset(
            [
                HostName("abc"),
                HostName("xyz"),
                HostName("lvl1"),
                HostName("lvl2"),
                HostName("lvl1a"),
            ]
        ),
        clusters_of={},
        nodes_of={},
    )

    assert not list(matcher.get_host_values(HostName("xyz"), ruleset=ruleset))
    assert list(matcher.get_host_values(HostName("lvl1"), ruleset=ruleset)) == ["LEVEL1"]
    assert list(matcher.get_host_values(HostName("lvl2"), ruleset=ruleset)) == [
        "LEVEL1",
        "LEVEL2",
    ]
    assert not list(matcher.get_host_values(HostName("lvl1a"), ruleset=ruleset))


dict_ruleset: Sequence[RuleSpec[Mapping[str, str]]] = [
    {
        "id": "1",
        "value": {"hu": "BLA"},
        "condition": {
            "host_name": ["host1"],
        },
        "options": {},
    },
    {
        "id": "2",
        "value": {"ho": "BLA"},
        "condition": {
            "host_name": ["host1", "host2"],
        },
        "options": {},
    },
    {
        "id": "3",
        "value": {
            "hu": "BLUB",
            "he": "BLUB",
        },
        "condition": {
            "host_name": ["host1", "host2"],
        },
        "options": {},
    },
    {
        "id": "4",
        "value": {"hu": "BLA"},
        "condition": {
            "host_name": ["xyz"],
        },
        "options": {
            "disabled": True,
        },
    },
]


def test_basic_host_ruleset_get_merged_dict_values() -> None:
    matcher = RulesetMatcher(
        host_tags={
            HostName("abc"): {},
            HostName("xyz"): {},
            HostName("host1"): {},
            HostName("host2"): {},
        },
        host_paths={},
        label_manager=LabelManager(
            explicit_host_labels={},
            host_label_rules=(),
            service_label_rules=(),
            discovered_labels_of_service=lambda *args, **kw: {},
            builtin_host_labels={},
        ),
        all_configured_hosts=frozenset(
            [
                HostName("abc"),
                HostName("xyz"),
                HostName("host1"),
                HostName("host2"),
            ]
        ),
        clusters_of={},
        nodes_of={},
    )

    assert not matcher.get_host_merged_dict(HostName("abc"), ruleset=dict_ruleset)
    assert not matcher.get_host_merged_dict(HostName("xyz"), ruleset=dict_ruleset)
    assert matcher.get_host_merged_dict(HostName("host1"), ruleset=dict_ruleset) == {
        "hu": "BLA",
        "ho": "BLA",
        "he": "BLUB",
    }
    assert matcher.get_host_merged_dict(HostName("host2"), ruleset=dict_ruleset) == {
        "hu": "BLUB",
        "ho": "BLA",
        "he": "BLUB",
    }


binary_ruleset: list[RuleSpec] = [
    {
        "id": "1",
        "value": True,
        "condition": {
            "host_name": ["host1"],
        },
        "options": {},
    },
    {
        "id": "2",
        "value": False,
        "condition": {"host_name": ["host1", "host2"]},
        "options": {},
    },
    {
        "id": "3",
        "value": True,
        "condition": {
            "host_name": ["host1", "host2"],
        },
        "options": {},
    },
    {
        "id": "4",
        "value": True,
        "condition": {
            "host_name": ["xyz"],
        },
        "options": {
            "disabled": True,
        },
    },
]


def test_basic_host_ruleset_get_host_bool_value() -> None:
    matcher = RulesetMatcher(
        host_tags={
            HostName("abc"): {},
            HostName("xyz"): {},
            HostName("host1"): {},
            HostName("host2"): {},
        },
        host_paths={},
        label_manager=LabelManager(
            explicit_host_labels={},
            host_label_rules=(),
            service_label_rules=(),
            discovered_labels_of_service=lambda *args, **kw: {},
            builtin_host_labels={},
        ),
        all_configured_hosts=frozenset(
            [
                HostName("abc"),
                HostName("xyz"),
                HostName("host1"),
                HostName("host2"),
            ]
        ),
        clusters_of={},
        nodes_of={},
    )

    assert matcher.get_host_bool_value(HostName("abc"), ruleset=binary_ruleset) is False
    assert matcher.get_host_bool_value(HostName("xyz"), ruleset=binary_ruleset) is False
    assert matcher.get_host_bool_value(HostName("host1"), ruleset=binary_ruleset) is True
    assert matcher.get_host_bool_value(HostName("host2"), ruleset=binary_ruleset) is False


tag_ruleset: Sequence[RuleSpec[str]] = [
    # test simple tag match
    {
        "id": "id0",
        "value": "crit_prod",
        "condition": {
            "host_tags": {
                TagGroupID("criticality"): TagID("prod"),
            },
        },
        "options": {},
    },
    # test implicit AND
    {
        "id": "id1",
        "value": "prod_cmk-agent",
        "condition": {
            "host_tags": {
                TagGroupID("criticality"): TagID("prod"),
                TagGroupID("agent"): TagID("cmk-agent"),
            },
        },
        "options": {},
    },
    # test negation of tag
    {
        "id": "id2",
        "value": "not_lan",
        "condition": {"host_tags": {TagGroupID("networking"): {"$ne": TagID("lan")}}},
        "options": {},
    },
    # test $or
    {
        "id": "id3",
        "value": "wan_or_lan",
        "condition": {
            "host_tags": {
                TagGroupID("networking"): {
                    "$or": [
                        TagID("lan"),
                        TagID("wan"),
                    ],
                }
            }
        },
        "options": {},
    },
    # test $nor
    {
        "id": "id4",
        "value": "not_wan_and_not_lan",
        "condition": {
            "host_tags": {
                TagGroupID("networking"): {
                    "$nor": [
                        TagID("lan"),
                        TagID("wan"),
                    ],
                }
            }
        },
        "options": {},
    },
    # test unconditional match
    {
        "id": "id5",
        "value": "BLA",
        "condition": {},
        "options": {},
    },
]


@pytest.mark.parametrize(
    "hostname,expected_result",
    [
        (HostName("host1"), ["crit_prod", "prod_cmk-agent", "wan_or_lan", "BLA"]),
        (HostName("host2"), ["not_lan", "wan_or_lan", "BLA"]),
        (HostName("host3"), ["not_lan", "not_wan_and_not_lan", "BLA"]),
    ],
)
def test_ruleset_matcher_get_host_values_tags(
    hostname: HostName, expected_result: Sequence[str]
) -> None:
    matcher = RulesetMatcher(
        host_tags={
            HostName("host1"): {
                TagGroupID("criticality"): TagID("prod"),
                TagGroupID("agent"): TagID("cmk-agent"),
                TagGroupID("networking"): TagID("lan"),
            },
            HostName("host2"): {
                TagGroupID("criticality"): TagID("test"),
                TagGroupID("networking"): TagID("wan"),
            },
            HostName("host3"): {
                TagGroupID("criticality"): TagID("test"),
                TagGroupID("networking"): TagID("dmz"),
            },
        },
        host_paths={},
        label_manager=LabelManager(
            explicit_host_labels={},
            host_label_rules=(),
            service_label_rules=(),
            discovered_labels_of_service=lambda *args, **kw: {},
            builtin_host_labels={},
        ),
        all_configured_hosts=frozenset(
            [
                HostName("host1"),
                HostName("host2"),
                HostName("host3"),
            ]
        ),
        clusters_of={},
        nodes_of={},
    )
    assert list(matcher.get_host_values(hostname, ruleset=tag_ruleset)) == expected_result


@pytest.mark.parametrize(
    "rule_spec, expected_result",
    [
        pytest.param(
            {
                "value": "value",
                "condition": {
                    "host_tags": {
                        TagGroupID("grp1"): TagID("v1"),
                    },
                },
                "id": "01",
                "options": {},
            },
            ["value"],
            id="should match",
        ),
        pytest.param(
            {
                "value": "value",
                "condition": {
                    "host_tags": {
                        TagGroupID("grp2"): TagID("v1"),
                    },
                },
                "id": "02",
                "options": {},
            },
            [],
            id="should not match",
        ),
    ],
)
def test_ruleset_matcher_get_host_values_tags_duplicate_ids(
    monkeypatch: MonkeyPatch,
    rule_spec: RuleConditionsSpec,
    expected_result: Sequence[Any],
) -> None:
    ts = Scenario()
    add_tag_config = TagConfig.from_config(
        {
            "aux_tags": [],
            "tag_groups": [
                {
                    "id": TagGroupID("grp1"),
                    "tags": [
                        {
                            "aux_tags": [],
                            "id": TagID("v1"),
                            "title": "Value1",
                        },
                    ],
                    "title": "Group 1",
                },
                {
                    "id": TagGroupID("grp2"),
                    "tags": [
                        {
                            "aux_tags": [],
                            "id": TagID("v1"),
                            "title": "Value1",
                        },
                    ],
                    "title": "Group 2",
                },
            ],
        }
    )
    ts.tags += add_tag_config
    ts.add_host(
        HostName("host"),
        tags={
            TagGroupID("grp1"): TagID("v1"),
        },
    )
    config_cache = ts.apply(monkeypatch)
    matcher = config_cache.ruleset_matcher

    assert (
        list(
            matcher.get_host_values(HostName("host"), ruleset=[rule_spec])  # type: ignore[arg-type]
        )
        == expected_result
    )


service_label_ruleset: Sequence[RuleSpec[str]] = [
    # test simple label match
    {
        "id": "id0",
        "value": "os_linux",
        "condition": {
            "service_label_groups": [("and", [("and", "os:linux")])],
        },
        "options": {},
    },
    # test implicit AND and unicode value match
    {
        "id": "id1",
        "value": "abc",
        "condition": {
            "service_label_groups": [
                ("and", [("and", "os:linux")]),
                ("and", [("and", "abc:xä")]),
            ],
        },
        "options": {},
    },
    # test negation of label
    {
        "id": "id2",
        "value": "hu",
        "condition": {
            "service_label_groups": [("and", [("not", "hu:ha")])],
        },
        "options": {},
    },
    # test unconditional match
    {
        "id": "id3",
        "value": "BLA",
        "condition": {},
        "options": {},
    },
]


@pytest.mark.parametrize(
    "hostname,service_description,expected_result",
    [
        # Funny service description because the plug-in isn't loaded.
        # We could patch config.service_description, but this is easier:
        (
            HostName("host1"),
            ServiceName("Unimplemented check cpu_load"),
            ["os_linux", "abc", "BLA"],
        ),
        (HostName("host2"), ServiceName("Unimplemented check cpu_load"), ["hu", "BLA"]),
    ],
)
def test_ruleset_matcher_get_service_ruleset_values_labels(
    monkeypatch: MonkeyPatch,
    hostname: HostName,
    service_description: ServiceName,
    expected_result: Sequence[str],
) -> None:
    ts = Scenario()

    ts.add_host(HostName("host1"))
    ts.set_autochecks(
        HostName("host1"),
        [
            AutocheckEntry(
                CheckPluginName("cpu_load"),
                None,
                {},
                {
                    "os": "linux",
                    "abc": "xä",
                    "hu": "ha",
                },
            )
        ],
    )

    ts.add_host(HostName("host2"))
    ts.set_autochecks(
        HostName("host2"),
        [
            AutocheckEntry(
                CheckPluginName("cpu_load"),
                None,
                {},
                {},
            ),
        ],
    )

    config_cache = ts.apply(monkeypatch)
    matcher = config_cache.ruleset_matcher

    assert (
        list(
            matcher.get_service_ruleset_values(
                matcher._service_match_object(hostname, service_description),
                ruleset=service_label_ruleset,
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    "taggroud_id, tag_condition, expected_result",
    [
        pytest.param(
            "t1",
            "abc",
            True,
            id="direct check if tag is present, true",
        ),
        pytest.param(
            "t-1",
            "abc",
            False,
            id="direct check if tag is present, non-existing tag group",
        ),
        pytest.param(
            "t1",
            "xyz",
            False,
            id="direct check if tag is present, wrong tag id",
        ),
        pytest.param(
            "t2",
            {"$ne": "789"},
            True,
            id="negated condition, true",
        ),
        pytest.param(
            "t-2",
            {"$ne": "789"},
            True,
            id="negated condition, non-existing tag group",
        ),
        pytest.param(
            "t2",
            {"$ne": "xyz"},
            False,
            id="negated condition, right tag id",
        ),
        pytest.param(
            "t3",
            {"$or": ["abc", "123"]},
            True,
            id="or condition, true",
        ),
        pytest.param(
            "t-3",
            {"$or": ["abc", "123"]},
            False,
            id="or condition, non-existing tag group",
        ),
        pytest.param(
            "t3",
            {"$or": ["abc", "456"]},
            False,
            id="or condition, wrong tag ids",
        ),
        pytest.param(
            "t4",
            {"$nor": ["efg", "789"]},
            True,
            id="nor condition, true",
        ),
        pytest.param(
            "t-4",
            {"$nor": ["efg", "789"]},
            True,
            id="nor condition, non-existing tag group",
        ),
        pytest.param(
            "t4",
            {"$nor": ["456", "789"]},
            False,
            id="nor condition, one right tag id",
        ),
    ],
)
def test_matches_tag_condition(
    taggroud_id: TagGroupID,
    tag_condition: TagCondition,
    expected_result: bool,
) -> None:
    assert (
        matches_tag_condition(
            taggroud_id,
            tag_condition,
            {
                (TagGroupID("t1"), TagID("abc")),
                (TagGroupID("t2"), TagID("xyz")),
                (TagGroupID("t3"), TagID("123")),
                (TagGroupID("t4"), TagID("456")),
            },
        )
        is expected_result
    )
