#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Sequence

import pytest
from _pytest.monkeypatch import MonkeyPatch

from tests.testlib.base import Scenario

from cmk.utils.rulesets.ruleset_matcher import matches_tag_condition, RulesetMatchObject
from cmk.utils.tags import TagConfig
from cmk.utils.type_defs import (
    CheckPluginName,
    HostName,
    RuleConditionsSpec,
    RuleSpec,
    RuleValue,
    ServiceName,
    TagCondition,
    TaggroupID,
)

from cmk.base.autochecks import AutocheckEntry


def test_ruleset_match_object_no_conditions() -> None:
    x = RulesetMatchObject(host_name=None, service_description=None)
    assert x.host_name is None
    assert x.service_description is None


def test_ruleset_match_object_host_name() -> None:
    obj = RulesetMatchObject(host_name=HostName("abc"), service_description=None)
    assert obj.host_name == "abc"


def test_ruleset_match_object_service_description() -> None:
    obj = RulesetMatchObject(host_name=None, service_description="Ümlaut")
    assert obj.service_description == "Ümlaut"


def test_ruleset_match_object_service_cache_id() -> None:
    obj1 = RulesetMatchObject(
        host_name=HostName("host"),
        service_description="svc",
        service_labels={"a": "v1"},
    )
    obj2 = RulesetMatchObject(
        host_name=HostName("host"),
        service_description="svc",
        service_labels={"a": "v2"},
    )
    assert obj1.service_cache_id != obj2.service_cache_id


def test_ruleset_match_object_service_cache_id_no_labels() -> None:
    obj = RulesetMatchObject(host_name=HostName("host"), service_description="svc")
    assert obj.service_cache_id == ("svc", hash(None))


ruleset: List[RuleSpec] = [
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

host_label_ruleset = [
    # test simple label match
    {
        "value": "os_linux",
        "condition": {
            "host_labels": {
                "os": "linux",
            },
        },
        "options": {},
    },
    # test implicit AND and unicode value match
    {
        "value": "abc",
        "condition": {
            "host_labels": {
                "os": "linux",
                "abc": "xä",
            },
        },
        "options": {},
    },
    # test negation of label
    {
        "value": "hu",
        "condition": {"host_labels": {"hu": {"$ne": "ha"}}},
        "options": {},
    },
    # test unconditional match
    {
        "value": "BLA",
        "condition": {},
        "options": {},
    },
]


@pytest.mark.parametrize(
    "hostname_str,expected_result",
    [
        ("host1", ["os_linux", "abc", "BLA"]),
        ("host2", ["hu", "BLA"]),
    ],
)
def test_ruleset_matcher_get_host_ruleset_values_labels(
    monkeypatch: MonkeyPatch, hostname_str: str, expected_result: Sequence[str]
) -> None:
    ts = Scenario()
    ts.add_host(HostName("host1"), labels={"os": "linux", "abc": "xä", "hu": "ha"})
    ts.add_host(HostName("host2"))
    config_cache = ts.apply(monkeypatch)
    matcher = config_cache.ruleset_matcher

    assert (
        list(
            matcher.get_host_ruleset_values(
                RulesetMatchObject(host_name=HostName(hostname_str), service_description=None),
                ruleset=host_label_ruleset,
                is_binary=False,
            )
        )
        == expected_result
    )


def test_basic_get_host_ruleset_values(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.add_host(HostName("abc"))
    ts.add_host(HostName("xyz"))
    ts.add_host(HostName("host1"))
    ts.add_host(HostName("host2"))
    config_cache = ts.apply(monkeypatch)
    matcher = config_cache.ruleset_matcher

    assert (
        list(
            matcher.get_host_ruleset_values(
                RulesetMatchObject(host_name=HostName("abc"), service_description=None),
                ruleset=ruleset,
                is_binary=False,
            )
        )
        == []
    )
    assert (
        list(
            matcher.get_host_ruleset_values(
                RulesetMatchObject(host_name=HostName("xyz"), service_description=None),
                ruleset=ruleset,
                is_binary=False,
            )
        )
        == []
    )
    assert list(
        matcher.get_host_ruleset_values(
            RulesetMatchObject(host_name=HostName("host1"), service_description=None),
            ruleset=ruleset,
            is_binary=False,
        )
    ) == ["BLA", "BLUB"]
    assert list(
        matcher.get_host_ruleset_values(
            RulesetMatchObject(host_name=HostName("host2"), service_description=None),
            ruleset=ruleset,
            is_binary=False,
        )
    ) == ["BLUB"]


def test_basic_get_host_ruleset_values_subfolders(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.add_host(HostName("abc"))
    ts.add_host(HostName("xyz"))
    ts.add_host(HostName("lvl1"), host_path="/lvl1/hosts.mk")
    ts.add_host(HostName("lvl2"), host_path="/lvl1/lvl2/hosts.mk")
    ts.add_host(HostName("lvl1a"), host_path="/lvl1_a/hosts.mk")
    config_cache = ts.apply(monkeypatch)
    matcher = config_cache.ruleset_matcher

    assert (
        list(
            matcher.get_host_ruleset_values(
                RulesetMatchObject(host_name=HostName("xyz"), service_description=None),
                ruleset=ruleset,
                is_binary=False,
            )
        )
        == []
    )
    assert list(
        matcher.get_host_ruleset_values(
            RulesetMatchObject(host_name=HostName("lvl1"), service_description=None),
            ruleset=ruleset,
            is_binary=False,
        )
    ) == ["LEVEL1"]
    assert list(
        matcher.get_host_ruleset_values(
            RulesetMatchObject(host_name=HostName("lvl2"), service_description=None),
            ruleset=ruleset,
            is_binary=False,
        )
    ) == ["LEVEL1", "LEVEL2"]
    assert (
        list(
            matcher.get_host_ruleset_values(
                RulesetMatchObject(host_name=HostName("lvl1a"), service_description=None),
                ruleset=ruleset,
                is_binary=False,
            )
        )
        == []
    )


dict_ruleset: List[RuleSpec] = [
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


def test_basic_host_ruleset_get_merged_dict_values(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.add_host(HostName("abc"))
    ts.add_host(HostName("abc"))
    ts.add_host(HostName("xyz"))
    ts.add_host(HostName("host1"))
    ts.add_host(HostName("host2"))
    config_cache = ts.apply(monkeypatch)

    matcher = config_cache.ruleset_matcher
    assert (
        matcher.get_host_ruleset_merged_dict(
            RulesetMatchObject(host_name=HostName("abc"), service_description=None),
            ruleset=dict_ruleset,
        )
        == {}
    )
    assert (
        matcher.get_host_ruleset_merged_dict(
            RulesetMatchObject(host_name=HostName("xyz"), service_description=None),
            ruleset=dict_ruleset,
        )
        == {}
    )
    assert matcher.get_host_ruleset_merged_dict(
        RulesetMatchObject(host_name=HostName("host1"), service_description=None),
        ruleset=dict_ruleset,
    ) == {
        "hu": "BLA",
        "ho": "BLA",
        "he": "BLUB",
    }
    assert matcher.get_host_ruleset_merged_dict(
        RulesetMatchObject(host_name=HostName("host2"), service_description=None),
        ruleset=dict_ruleset,
    ) == {
        "hu": "BLUB",
        "ho": "BLA",
        "he": "BLUB",
    }


binary_ruleset: List[RuleSpec] = [
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


def test_basic_host_ruleset_is_matching_host_ruleset(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.add_host(HostName("abc"))
    ts.add_host(HostName("abc"))
    ts.add_host(HostName("xyz"))
    ts.add_host(HostName("host1"))
    ts.add_host(HostName("host2"))
    config_cache = ts.apply(monkeypatch)

    matcher = config_cache.ruleset_matcher
    assert (
        matcher.is_matching_host_ruleset(
            RulesetMatchObject(host_name=HostName("abc"), service_description=None),
            ruleset=binary_ruleset,
        )
        is False
    )
    assert (
        matcher.is_matching_host_ruleset(
            RulesetMatchObject(host_name=HostName("xyz"), service_description=None),
            ruleset=binary_ruleset,
        )
        is False
    )
    assert (
        matcher.is_matching_host_ruleset(
            RulesetMatchObject(host_name=HostName("host1"), service_description=None),
            ruleset=binary_ruleset,
        )
        is True
    )
    assert (
        matcher.is_matching_host_ruleset(
            RulesetMatchObject(host_name=HostName("host2"), service_description=None),
            ruleset=binary_ruleset,
        )
        is False
    )


tag_ruleset = [
    # test simple tag match
    {
        "value": "crit_prod",
        "condition": {
            "host_tags": {
                "criticality": "prod",
            },
        },
        "options": {},
    },
    # test implicit AND
    {
        "value": "prod_cmk-agent",
        "condition": {
            "host_tags": {
                "criticality": "prod",
                "agent": "cmk-agent",
            },
        },
        "options": {},
    },
    # test negation of tag
    {
        "value": "not_lan",
        "condition": {"host_tags": {"networking": {"$ne": "lan"}}},
        "options": {},
    },
    # test $or
    {
        "value": "wan_or_lan",
        "condition": {
            "host_tags": {
                "networking": {
                    "$or": [
                        "lan",
                        "wan",
                    ],
                }
            }
        },
        "options": {},
    },
    # test $nor
    {
        "value": "not_wan_and_not_lan",
        "condition": {
            "host_tags": {
                "networking": {
                    "$nor": [
                        "lan",
                        "wan",
                    ],
                }
            }
        },
        "options": {},
    },
    # test unconditional match
    {
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
def test_ruleset_matcher_get_host_ruleset_values_tags(
    monkeypatch: MonkeyPatch,
    hostname: HostName,
    expected_result: Sequence[str],
) -> None:
    ts = Scenario()
    ts.add_host(
        HostName("host1"),
        tags={
            "criticality": "prod",
            "agent": "cmk-agent",
            "networking": "lan",
        },
    )
    ts.add_host(
        HostName("host2"),
        tags={
            "criticality": "test",
            "networking": "wan",
        },
    )
    ts.add_host(
        HostName("host3"),
        tags={
            "criticality": "test",
            "networking": "dmz",
        },
    )
    config_cache = ts.apply(monkeypatch)
    matcher = config_cache.ruleset_matcher

    assert (
        list(
            matcher.get_host_ruleset_values(
                RulesetMatchObject(host_name=hostname, service_description=None),
                ruleset=tag_ruleset,
                is_binary=False,
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    "rule_spec, expected_result",
    [
        pytest.param(
            {
                "value": "value",
                "condition": {
                    "host_tags": {
                        "grp1": "v1",
                    },
                },
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
                        "grp2": "v1",
                    },
                },
                "options": {},
            },
            [],
            id="should not match",
        ),
    ],
)
def test_ruleset_matcher_get_host_ruleset_values_tags_duplicate_ids(
    monkeypatch: MonkeyPatch,
    rule_spec: RuleConditionsSpec,
    expected_result: Sequence[RuleValue],
) -> None:
    ts = Scenario()
    add_tag_config = TagConfig.from_config(
        {
            "aux_tags": [],
            "tag_groups": [
                {
                    "id": "grp1",
                    "tags": [
                        {
                            "aux_tags": [],
                            "id": "v1",
                            "title": "Value1",
                        },
                    ],
                    "title": "Group 1",
                },
                {
                    "id": "grp2",
                    "tags": [
                        {
                            "aux_tags": [],
                            "id": "v1",
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
        "host",
        tags={
            "grp1": "v1",
        },
    )
    config_cache = ts.apply(monkeypatch)
    matcher = config_cache.ruleset_matcher

    assert (
        list(
            matcher.get_host_ruleset_values(
                RulesetMatchObject(
                    host_name=HostName("host"),
                    service_description=None,
                ),
                ruleset=[rule_spec],
                is_binary=False,
            )
        )
        == expected_result
    )


service_label_ruleset = [
    # test simple label match
    {
        "value": "os_linux",
        "condition": {
            "service_labels": {
                "os": "linux",
            },
        },
        "options": {},
    },
    # test implicit AND and unicode value match
    {
        "value": "abc",
        "condition": {
            "service_labels": {
                "os": "linux",
                "abc": "xä",
            },
        },
        "options": {},
    },
    # test negation of label
    {
        "value": "hu",
        "condition": {"service_labels": {"hu": {"$ne": "ha"}}},
        "options": {},
    },
    # test unconditional match
    {
        "value": "BLA",
        "condition": {},
        "options": {},
    },
]


@pytest.mark.parametrize(
    "hostname,service_description,expected_result",
    [
        # Funny service description because the plugin isn't loaded.
        # We could patch config.service_description, but this is easier:
        (HostName("host1"), "Unimplemented check cpu_load", ["os_linux", "abc", "BLA"]),
        (HostName("host2"), "Unimplemented check cpu_load", ["hu", "BLA"]),
    ],
)
def test_ruleset_matcher_get_service_ruleset_values_labels(
    monkeypatch: MonkeyPatch,
    hostname: HostName,
    service_description: str,
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
                config_cache.ruleset_match_object_of_service(
                    hostname, ServiceName(service_description)
                ),
                ruleset=service_label_ruleset,
                is_binary=False,
            )
        )
        == expected_result
    )


def test_ruleset_optimizer_clear_ruleset_caches(monkeypatch: MonkeyPatch) -> None:
    config_cache = Scenario().apply(monkeypatch)
    ruleset_optimizer = config_cache.ruleset_matcher.ruleset_optimizer
    ruleset_optimizer.get_service_ruleset(ruleset, False, False)
    ruleset_optimizer.get_host_ruleset(ruleset, False, False)
    assert ruleset_optimizer._host_ruleset_cache
    assert ruleset_optimizer._service_ruleset_cache
    ruleset_optimizer.clear_ruleset_caches()
    assert not ruleset_optimizer._host_ruleset_cache
    assert not ruleset_optimizer._service_ruleset_cache


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
    taggroud_id: TaggroupID,
    tag_condition: TagCondition,
    expected_result: bool,
) -> None:
    assert (
        matches_tag_condition(
            taggroud_id,
            tag_condition,
            {
                ("t1", "abc"),
                ("t2", "xyz"),
                ("t3", "123"),
                ("t4", "456"),
            },
        )
        is expected_result
    )
