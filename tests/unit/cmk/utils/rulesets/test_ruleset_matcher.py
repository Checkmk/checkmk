#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from pytest import MonkeyPatch

from tests.testlib.base import Scenario

import cmk.utils.paths
from cmk.utils.rulesets.ruleset_matcher import (
    matches_tag_condition,
    RuleConditionsSpec,
    RulesetMatchObject,
    RuleSpec,
    TagCondition,
)
from cmk.utils.tags import TagConfig, TagGroupID
from cmk.utils.type_defs import CheckPluginName, HostName, ServiceName

from cmk.checkers.discovery import AutocheckEntry


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
            "host_labels": {
                "os": "linux",
            },
        },
        "options": {},
    },
    # test implicit AND and unicode value match
    {
        "id": "id1",
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
        "id": "id2",
        "value": "hu",
        "condition": {"host_labels": {"hu": {"$ne": "ha"}}},
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


def test_labels_of_service(monkeypatch: MonkeyPatch) -> None:
    test_host = HostName("test-host")
    xyz_host = HostName("xyz")
    ts = Scenario()
    ts.set_ruleset(
        "service_label_rules",
        [
            {
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_tags": {"agent": "no-agent"},
                },
                "value": {"label1": "val1"},
            },
            {
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_tags": {"agent": "no-agent"},
                },
                "value": {"label2": "val2"},
            },
        ],
    )

    ts.add_host(test_host, tags={"agent": "no-agent"})
    ruleset_matcher = ts.apply(monkeypatch).ruleset_matcher

    assert ruleset_matcher.labels_of_service(xyz_host, "CPU load") == {}
    assert ruleset_matcher.label_sources_of_service(xyz_host, "CPU load") == {}

    assert ruleset_matcher.labels_of_service(test_host, "CPU load") == {
        "label1": "val1",
        "label2": "val2",
    }
    assert ruleset_matcher.label_sources_of_service(test_host, "CPU load") == {
        "label1": "ruleset",
        "label2": "ruleset",
    }


@pytest.mark.usefixtures("fix_register")
def test_labels_of_service_discovered_labels(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    test_host = HostName("test-host")
    xyz_host = HostName("xyz")
    ts = Scenario()
    ts.add_host(test_host)

    monkeypatch.setattr(cmk.utils.paths, "autochecks_dir", str(tmp_path))
    autochecks_file = Path(cmk.utils.paths.autochecks_dir, "test-host.mk")
    with autochecks_file.open("w", encoding="utf-8") as f:
        f.write(
            """[
    {'check_plugin_name': 'cpu_loads', 'item': None, 'parameters': (5.0, 10.0), 'service_labels': {u'äzzzz': u'eeeeez'}},
]"""
        )

    config_cache = ts.apply(monkeypatch)
    ruleset_matcher = config_cache.ruleset_matcher

    service = config_cache.get_autochecks_of(test_host)[0]
    assert service.description == "CPU load"

    assert ruleset_matcher.labels_of_service(xyz_host, "CPU load") == {}
    assert ruleset_matcher.label_sources_of_service(xyz_host, "CPU load") == {}

    assert ruleset_matcher.labels_of_service(test_host, service.description) == {"äzzzz": "eeeeez"}
    assert ruleset_matcher.label_sources_of_service(test_host, service.description) == {
        "äzzzz": "discovered"
    }


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


dict_ruleset: Sequence[RuleSpec[dict[str, str]]] = [
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


tag_ruleset: Sequence[RuleSpec[str]] = [
    # test simple tag match
    {
        "id": "id0",
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
        "id": "id1",
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
        "id": "id2",
        "value": "not_lan",
        "condition": {"host_tags": {"networking": {"$ne": "lan"}}},
        "options": {},
    },
    # test $or
    {
        "id": "id3",
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
        "id": "id4",
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
    expected_result: Sequence[Any],
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
                ruleset=[rule_spec],  # type: ignore[arg-type]
                is_binary=False,
            )
        )
        == expected_result
    )


service_label_ruleset: Sequence[RuleSpec[str]] = [
    # test simple label match
    {
        "id": "id0",
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
        "id": "id1",
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
        "id": "id2",
        "value": "hu",
        "condition": {"service_labels": {"hu": {"$ne": "ha"}}},
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
    ruleset_optimizer.get_service_ruleset(ruleset, False)
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
    taggroud_id: TagGroupID,
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
