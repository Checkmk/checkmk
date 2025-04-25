#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Tests for legacy tuple rulesets.
"""

from collections.abc import Mapping, Sequence
from typing import Final

import pytest

from tests.testlib.unit.base_configuration_scenario import Scenario

import cmk.ccc.version as cmk_version
from cmk.ccc.hostaddress import HostName

from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from cmk.utils.rulesets.tuple_rulesets import (
    ALL_HOSTS,
    get_rule_options,
    hosttags_match_taglist,
    in_extraconf_hostlist,
    in_extraconf_servicelist,
)
from cmk.utils.tags import TagGroupID, TagID


@pytest.fixture(autouse=True)
def fake_version(monkeypatch):
    monkeypatch.setattr(cmk_version, "omd_version", lambda *args, **kw: "1.4.0i1.cee")


@pytest.fixture()
def ts(monkeypatch):
    ts = Scenario(site_id="site1")
    ts.add_host(
        HostName("host1"),
        tags={TagGroupID("agent"): TagID("no-agent"), TagGroupID("criticality"): TagID("test")},
    )
    ts.add_host(HostName("host2"), tags={TagGroupID("agent"): TagID("no-agent")})
    ts.add_host(
        HostName("host3"),
        tags={TagGroupID("agent"): TagID("no-agent"), TagGroupID("site"): TagID("site2")},
    )
    ts.apply(monkeypatch)
    return ts


def test_service_extra_conf(ts: Scenario) -> None:
    ruleset: Final[Sequence[RuleSpec[str]]] = [
        {"condition": {}, "id": "01", "options": {}, "value": "1"},
        {"condition": {}, "id": "02", "options": {}, "value": "2"},
        {
            "condition": {"host_tags": {TagGroupID("agent"): TagID("no-agent")}},
            "id": "03",
            "options": {},
            "value": "3",
        },
        {
            "condition": {"host_tags": {TagGroupID("criticality"): TagID("test")}},
            "id": "04",
            "options": {},
            "value": "4",
        },
        {
            "condition": {"host_tags": {TagGroupID("tag3"): TagID("tag3")}},
            "id": "05",
            "options": {},
            "value": "5",
        },
        {
            "condition": {"host_tags": {TagGroupID("tag3"): TagID("tag3")}, "host_name": ["host1"]},
            "id": "06",
            "options": {},
            "value": "6",
        },
        {"condition": {"host_name": ["host1"]}, "options": {}, "id": "07", "value": "7"},
        {
            "condition": {"service_description": [{"$regex": "service1$"}], "host_name": ["host1"]},
            "id": "08",
            "options": {},
            "value": "8",
        },
        {
            "condition": {"service_description": [{"$regex": "ser$"}], "host_name": ["host1"]},
            "id": "09",
            "options": {},
            "value": "9",
        },
        {
            "condition": {"service_description": [{"$regex": "^serv$"}], "host_name": ["host1"]},
            "id": "10",
            "options": {},
            "value": "10",
        },
        {
            "condition": {"host_name": [{"$regex": "host"}]},
            "id": "11",
            "options": {},
            "value": "11",
        },
        {"condition": {"host_name": {"$nor": ["host2"]}}, "id": "12", "options": {}, "value": "12"},
    ]

    matcher = ts.config_cache.ruleset_matcher
    label_manager = ts.config_cache.label_manager
    assert matcher.service_extra_conf(
        HostName("host1"), "service1", {}, ruleset, label_manager.labels_of_host
    ) == [
        "1",
        "2",
        "3",
        "4",
        "7",
        "8",
        "11",
        "12",
    ]

    assert matcher.service_extra_conf(
        HostName("host1"), "serv", {}, ruleset, label_manager.labels_of_host
    ) == [
        "1",
        "2",
        "3",
        "4",
        "7",
        "10",
        "11",
        "12",
    ]

    assert matcher.service_extra_conf(
        HostName("host2"), "service1", {}, ruleset, label_manager.labels_of_host
    ) == [
        "1",
        "2",
        "3",
        "11",
    ]


HOST_RULESET: Final[Sequence[RuleSpec[Mapping[str, bool]]]] = [
    {"condition": {}, "id": "01", "options": {}, "value": {"1": True}},
    {
        "condition": {"host_tags": {TagGroupID("agent"): TagID("no-agent")}},
        "id": "02",
        "options": {},
        "value": {"2": True},
    },
    {
        "condition": {"host_tags": {TagGroupID("criticality"): TagID("test")}},
        "id": "03",
        "options": {},
        "value": {"3": True},
    },
    {
        "condition": {"host_tags": {TagGroupID("tag3"): TagID("tag3")}},
        "id": "04",
        "options": {},
        "value": {"4": True},
    },
    {
        "condition": {
            "host_tags": {TagGroupID("agent"): TagID("no-agent")},
            "host_name": ["host1"],
        },
        "id": "05",
        "options": {},
        "value": {"5": True},
    },
    {
        "condition": {"host_tags": {TagGroupID("tag3"): TagID("tag3")}, "host_name": ["host1"]},
        "id": "06",
        "options": {},
        "value": {"6": True},
    },
    {"condition": {"host_name": ["host1"]}, "id": "07", "options": {}, "value": {"7": True}},
    {
        "condition": {"host_name": [{"$regex": "host"}]},
        "id": "08",
        "options": {},
        "value": {"8": True},
    },
    {
        "condition": {"host_name": {"$nor": ["host2"]}},
        "id": "09",
        "options": {},
        "value": {"9": True},
    },
]


def test_get_host_values(ts: Scenario) -> None:
    ruleset_matcher = ts.config_cache.ruleset_matcher
    label_manager = ts.config_cache.label_manager
    assert ruleset_matcher.get_host_values(
        HostName("host1"), HOST_RULESET, label_manager.labels_of_host
    ) == [
        {"1": True},
        {"2": True},
        {"3": True},
        {"5": True},
        {"7": True},
        {"8": True},
        {"9": True},
    ]

    assert ruleset_matcher.get_host_values(
        HostName("host2"), HOST_RULESET, label_manager.labels_of_host
    ) == [
        {"1": True},
        {"2": True},
        {"8": True},
    ]


def test_get_host_merged_dict(ts: Scenario) -> None:
    ruleset_matcher = ts.config_cache.ruleset_matcher
    label_manager = ts.config_cache.label_manager
    assert ruleset_matcher.get_host_merged_dict(
        HostName("host1"), HOST_RULESET, label_manager.labels_of_host
    ) == {
        "1": True,
        "2": True,
        "3": True,
        "5": True,
        "7": True,
        "8": True,
        "9": True,
    }

    assert ruleset_matcher.get_host_merged_dict(
        HostName("host2"), HOST_RULESET, label_manager.labels_of_host
    ) == {
        "1": True,
        "2": True,
        "8": True,
    }


@pytest.mark.parametrize(
    "parameters",
    [
        # ruleset, outcome host1, outcome host2
        ([], False, False),
        (
            [{"condition": {}, "id": "01", "options": {}, "value": False}],
            False,
            False,
        ),
        ([{"condition": {}, "id": "02", "options": {}, "value": True}], True, True),
        (
            [
                {
                    "condition": {"host_name": {"$nor": ["host1"]}},
                    "id": "03",
                    "options": {},
                    "value": True,
                }
            ],
            False,
            True,
        ),
        (
            [
                {
                    "condition": {"host_name": {"$nor": ["host1", "host2"]}},
                    "id": "04",
                    "options": {},
                    "value": True,
                }
            ],
            False,
            False,
        ),
        (
            [
                {
                    "condition": {"host_tags": {TagGroupID("criticality"): TagID("test")}},
                    "id": "05",
                    "options": {},
                    "value": True,
                }
            ],
            True,
            False,
        ),
        (
            [
                {
                    "condition": {
                        "host_tags": {TagGroupID("criticality"): TagID("test")},
                        "host_name": {"$nor": ["host1"]},
                    },
                    "id": "06",
                    "options": {},
                    "value": True,
                }
            ],
            False,
            False,
        ),
        (
            [
                {
                    "condition": {"host_name": {"$nor": ["host1"]}},
                    "id": "07",
                    "options": {},
                    "value": True,
                }
            ],
            False,
            True,
        ),
        (
            [
                {
                    "condition": {"host_name": {"$nor": ["host1"]}},
                    "id": "08",
                    "options": {},
                    "value": False,
                }
            ],
            False,
            False,
        ),
        (
            [
                {
                    "condition": {
                        "host_tags": {TagGroupID("criticality"): TagID("test")},
                        "host_name": {"$nor": ["host1"]},
                    },
                    "id": "08",
                    "options": {},
                    "value": False,
                }
            ],
            False,
            False,
        ),
        (
            [
                {
                    "condition": {"service_description": [{"$regex": "serv"}]},
                    "id": "09",
                    "options": {},
                    "value": True,
                }
            ],
            True,
            True,
        ),
        (
            [
                {
                    "condition": {"service_description": [{"$regex": "serv"}]},
                    "id": "10",
                    "options": {},
                    "value": False,
                }
            ],
            False,
            False,
        ),
        (
            [
                {
                    "condition": {"service_description": [{"$regex": "service1"}]},
                    "id": "11",
                    "options": {},
                    "value": False,
                }
            ],
            False,
            False,
        ),
        # Dual rule test, first rule matches host1 - negates -> False
        #                 second rule matches host2 -> True
        (
            [
                {
                    "condition": {"service_description": [{"$regex": "service1"}]},
                    "id": "12",
                    "options": {},
                    "value": False,
                },
                {"condition": {}, "id": "13", "options": {}, "value": True},
            ],
            False,
            True,
        ),
    ],
)
def test_get_service_bool_value(
    ts: Scenario, parameters: tuple[Sequence[RuleSpec], bool, bool]
) -> None:
    ruleset, outcome_host1, outcome_host2 = parameters
    matcher = ts.config_cache.ruleset_matcher
    label_manager = ts.config_cache.label_manager

    assert (
        matcher.get_service_bool_value(
            HostName("host1"), "service1", {}, ruleset, label_manager.labels_of_host
        )
        == outcome_host1
    )
    assert (
        matcher.get_service_bool_value(
            HostName("host2"), "service2", {}, ruleset, label_manager.labels_of_host
        )
        == outcome_host2
    )


def test_all_matching_hosts(ts: Scenario) -> None:
    ruleset_matcher = ts.config_cache.ruleset_matcher
    label_manager = ts.config_cache.label_manager
    assert ruleset_matcher.ruleset_optimizer._all_matching_hosts(
        {"host_tags": {TagGroupID("agent"): TagID("no-agent")}},
        with_foreign_hosts=False,
        labels_of_host=label_manager.labels_of_host,
    ) == {"host1", "host2"}

    assert ruleset_matcher.ruleset_optimizer._all_matching_hosts(
        {"host_tags": {TagGroupID("criticality"): TagID("test")}},
        with_foreign_hosts=False,
        labels_of_host=label_manager.labels_of_host,
    ) == {"host1"}

    assert ruleset_matcher.ruleset_optimizer._all_matching_hosts(
        {"host_tags": {TagGroupID("criticality"): {"$ne": TagID("test")}}},
        with_foreign_hosts=False,
        labels_of_host=label_manager.labels_of_host,
    ) == {"host2"}

    assert ruleset_matcher.ruleset_optimizer._all_matching_hosts(
        {"host_tags": {TagGroupID("criticality"): {"$ne": TagID("test")}}},
        with_foreign_hosts=True,
        labels_of_host=label_manager.labels_of_host,
    ) == {"host2", "host3"}

    assert (
        ruleset_matcher.ruleset_optimizer._all_matching_hosts(
            {"host_tags": {TagGroupID("agent"): TagID("no-agent")}, "host_name": []},
            with_foreign_hosts=True,
            labels_of_host=label_manager.labels_of_host,
        )
        == set()
    )

    assert ruleset_matcher.ruleset_optimizer._all_matching_hosts(
        {"host_tags": {TagGroupID("agent"): TagID("no-agent")}, "host_name": ["host1"]},
        with_foreign_hosts=True,
        labels_of_host=label_manager.labels_of_host,
    ) == {"host1"}

    assert (
        ruleset_matcher.ruleset_optimizer._all_matching_hosts(
            {
                "host_tags": {TagGroupID("agent"): {"$ne": TagID("no-agent")}},
                "host_name": ["host1"],
            },
            with_foreign_hosts=False,
            labels_of_host=label_manager.labels_of_host,
        )
        == set()
    )

    assert ruleset_matcher.ruleset_optimizer._all_matching_hosts(
        {"host_tags": {TagGroupID("agent"): TagID("no-agent")}, "host_name": [{"$regex": "h"}]},
        with_foreign_hosts=False,
        labels_of_host=label_manager.labels_of_host,
    ) == {"host1", "host2"}

    assert ruleset_matcher.ruleset_optimizer._all_matching_hosts(
        {"host_tags": {TagGroupID("agent"): TagID("no-agent")}, "host_name": [{"$regex": ".*2"}]},
        with_foreign_hosts=False,
        labels_of_host=label_manager.labels_of_host,
    ) == {"host2"}

    assert ruleset_matcher.ruleset_optimizer._all_matching_hosts(
        {"host_tags": {TagGroupID("agent"): TagID("no-agent")}, "host_name": [{"$regex": ".*2$"}]},
        with_foreign_hosts=False,
        labels_of_host=label_manager.labels_of_host,
    ) == {"host2"}

    assert (
        ruleset_matcher.ruleset_optimizer._all_matching_hosts(
            {"host_tags": {TagGroupID("agent"): TagID("no-agent")}, "host_name": [{"$regex": "2"}]},
            with_foreign_hosts=False,
            labels_of_host=label_manager.labels_of_host,
        )
        == set()
    )


def test_in_extraconf_hostlist() -> None:
    assert in_extraconf_hostlist(ALL_HOSTS, "host1") is True
    assert in_extraconf_hostlist([], "host1") is False

    assert in_extraconf_hostlist(["host2", "host1"], "host1") is True
    assert in_extraconf_hostlist(["host1", "host2"], "host1") is True

    assert in_extraconf_hostlist(["host1"], "host1") is True
    assert in_extraconf_hostlist(["!host1", "host1", "!host1"], "host1") is False
    assert in_extraconf_hostlist(["!host1"], "host1") is False
    assert in_extraconf_hostlist(["!host2"], "host1") is False
    assert in_extraconf_hostlist(["host1", "!host2"], "host1") is True
    assert in_extraconf_hostlist(["!host2", "host1"], "host1") is True
    assert in_extraconf_hostlist(["~h"], "host1") is True
    assert in_extraconf_hostlist(["~h"], "host1") is True
    assert in_extraconf_hostlist(["~h$"], "host1") is False
    assert in_extraconf_hostlist(["~1"], "host1") is False
    assert in_extraconf_hostlist(["~.*1"], "host1") is True
    assert in_extraconf_hostlist(["~.*1$"], "host1") is True


def test_get_rule_options_regular_rule() -> None:
    options = {"description": 'Put all hosts into the contact group "all"'}
    entry: tuple[str, list[str], list[str], dict] = ("all", [], ALL_HOSTS, options)
    assert get_rule_options(entry) == (entry[:-1], options)


def test_get_rule_options_empty_options() -> None:
    options: dict = {}
    entry: tuple[str, list[str], list[str], dict] = ("all", [], ALL_HOSTS, options)
    assert get_rule_options(entry) == (entry[:-1], options)


def test_get_rule_options_missing_options() -> None:
    entry: tuple[str, list[str], list[str]] = ("all", [], ALL_HOSTS)
    assert get_rule_options(entry) == (entry, {})


def test_hosttags_match_taglist() -> None:
    assert hosttags_match_taglist([TagID("no-agent")], [TagID("no-agent")])
    assert hosttags_match_taglist([TagID("no-agent"), TagID("test")], [TagID("no-agent")])
    assert hosttags_match_taglist(
        [TagID("no-agent"), TagID("test")], [TagID("no-agent"), TagID("test")]
    )


def test_hosttags_match_taglist_not_matching() -> None:
    assert not hosttags_match_taglist([TagID("no-agent")], [TagID("test")])
    assert not hosttags_match_taglist(
        [TagID("tag"), TagID("no-agent"), TagID("test2")], [TagID("test")]
    )
    assert not hosttags_match_taglist(
        [TagID("no-agent"), TagID("test")], [TagID("test"), TagID("tag3")]
    )


def test_hosttags_match_taglist_negate() -> None:
    assert not hosttags_match_taglist(
        [TagID("no-agent"), TagID("test")], [TagID("no-agent"), TagID("!test")]
    )
    assert hosttags_match_taglist([TagID("no-agent")], [TagID("no-agent"), TagID("!test")])


@pytest.mark.parametrize(
    "service_patterns,service,expected",
    [
        ([], "Disk IO SUMMARY", False),
        ([""], "", True),
        ([""], "Disk IO SUMMARY", True),
        (["!"], "", True),
        (["!"], "Disk IO SUMMARY", True),
        (["!!"], "!", False),
        (["!!"], "a", True),
        (["$"], "", True),
        (["$"], "a", False),
        (["!$"], "", False),
        (["!$"], "a", True),
        (["."], "", False),
        (["."], "a", True),
        (["."], "aa", True),
        ([".$"], "aa", False),
        ([".*"], "", True),
        ([".*"], "Filesystem /", True),
        (["Interface 1"], "Interface 1", True),
        (["Interface 1"], "interface 1", False),
        (["!Filesystem /"], "Filesystem /", False),
        (["!Filesystem /"], "Filesystem /boot", False),
        (["!Filesystem /$"], "Filesystem /boot", True),
        (["Interface 1", "Interface 2"], "Interface 2", True),
        (["Interface 1", "Interface 2"], "Interface 22", True),
        (["Interface 1", "Interface 2"], "Interface 3", False),
        (["Interface 1", "!Interface 2", "Interface 3"], "Interface 2", False),
        (["Memory$"], "Mem", False),
        (["Memory$"], "Memory", True),
        (["Memory$"], "Memory used", False),
        (["OMD heute .*"], "OMD heute performance", True),
        (["OMD heute .*"], "OMD heute ", True),
        (["OMD heute .*"], "OMD heute", False),
        (["!^OMD .* performance$"], "OMD stable performance", False),
        ([r"OMD ([a-z]+) \1"], "OMD stable stable", True),
    ],
)
def test_in_extraconf_servicelist(
    service_patterns: list[str], service: str, expected: bool
) -> None:
    assert in_extraconf_servicelist(service_patterns, service) == expected
