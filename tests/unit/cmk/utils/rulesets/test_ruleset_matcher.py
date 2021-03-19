#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import pytest  # type: ignore[import]
from testlib.base import Scenario

from cmk.utils.type_defs import CheckPluginName
from cmk.base.check_utils import Service
from cmk.base.discovered_labels import DiscoveredServiceLabels, ServiceLabel
from cmk.utils.rulesets.ruleset_matcher import RulesetMatchObject


def test_ruleset_match_object_no_conditions():
    x = RulesetMatchObject(host_name=None, service_description=None)
    assert x.host_name is None
    assert x.service_description is None


def test_ruleset_match_object_host_name():
    obj = RulesetMatchObject(host_name="abc", service_description=None)
    assert obj.host_name == "abc"


def test_ruleset_match_object_service_description():
    obj = RulesetMatchObject(host_name=None, service_description=u"Ümlaut")
    assert obj.service_description == u"Ümlaut"


ruleset = [
    {
        "value": "BLA",
        "condition": {
            "host_name": ["host1"],
        },
        "options": {},
    },
    {
        "value": "BLUB",
        "condition": {
            "host_name": ["host1", "host2"]
        },
        "options": {},
    },
    {
        "value": "BLA",
        "condition": {
            "host_name": ["xyz"],
        },
        "options": {
            "disabled": True,
        },
    },
    {
        "value": "LEVEL1",
        "condition": {
            "host_folder": "/lvl1/"
        },
    },
    {
        "value": "LEVEL2",
        "condition": {
            "host_folder": "/lvl1/lvl2/"
        },
    },
    {
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
        "condition": {
            "host_labels": {
                "hu": {
                    "$ne": "ha"
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


@pytest.mark.parametrize("hostname,expected_result", [
    ("host1", ["os_linux", "abc", "BLA"]),
    ("host2", ["hu", "BLA"]),
])
def test_ruleset_matcher_get_host_ruleset_values_labels(monkeypatch, hostname, expected_result):
    ts = Scenario()
    ts.add_host("host1", labels={"os": "linux", "abc": "xä", "hu": "ha"})
    ts.add_host("host2")
    config_cache = ts.apply(monkeypatch)
    matcher = config_cache.ruleset_matcher

    assert list(
        matcher.get_host_ruleset_values(RulesetMatchObject(host_name=hostname,
                                                           service_description=None),
                                        ruleset=host_label_ruleset,
                                        is_binary=False)) == expected_result


def test_basic_get_host_ruleset_values(monkeypatch):
    ts = Scenario().add_host("abc")
    ts.add_host("xyz")
    ts.add_host("host1")
    ts.add_host("host2")
    config_cache = ts.apply(monkeypatch)
    matcher = config_cache.ruleset_matcher

    assert list(
        matcher.get_host_ruleset_values(RulesetMatchObject(host_name="abc",
                                                           service_description=None),
                                        ruleset=ruleset,
                                        is_binary=False)) == []
    assert list(
        matcher.get_host_ruleset_values(RulesetMatchObject(host_name="xyz",
                                                           service_description=None),
                                        ruleset=ruleset,
                                        is_binary=False)) == []
    assert list(
        matcher.get_host_ruleset_values(RulesetMatchObject(host_name="host1",
                                                           service_description=None),
                                        ruleset=ruleset,
                                        is_binary=False)) == ["BLA", "BLUB"]
    assert list(
        matcher.get_host_ruleset_values(RulesetMatchObject(host_name="host2",
                                                           service_description=None),
                                        ruleset=ruleset,
                                        is_binary=False)) == ["BLUB"]


def test_basic_get_host_ruleset_values_subfolders(monkeypatch):
    ts = Scenario().add_host("abc")
    ts.add_host("xyz")
    ts.add_host("lvl1", host_path="/lvl1/hosts.mk")
    ts.add_host("lvl2", host_path="/lvl1/lvl2/hosts.mk")
    ts.add_host("lvl1a", host_path="/lvl1_a/hosts.mk")
    config_cache = ts.apply(monkeypatch)
    matcher = config_cache.ruleset_matcher

    assert list(
        matcher.get_host_ruleset_values(RulesetMatchObject(host_name="xyz",
                                                           service_description=None),
                                        ruleset=ruleset,
                                        is_binary=False)) == []
    assert list(
        matcher.get_host_ruleset_values(RulesetMatchObject(host_name="lvl1",
                                                           service_description=None),
                                        ruleset=ruleset,
                                        is_binary=False)) == ["LEVEL1"]
    assert list(
        matcher.get_host_ruleset_values(RulesetMatchObject(host_name="lvl2",
                                                           service_description=None),
                                        ruleset=ruleset,
                                        is_binary=False)) == ["LEVEL1", "LEVEL2"]
    assert list(
        matcher.get_host_ruleset_values(RulesetMatchObject(host_name="lvl1a",
                                                           service_description=None),
                                        ruleset=ruleset,
                                        is_binary=False)) == []


dict_ruleset = [
    {
        "value": {
            "hu": "BLA"
        },
        "condition": {
            "host_name": ["host1"],
        },
        "options": {},
    },
    {
        "value": {
            "ho": "BLA"
        },
        "condition": {
            "host_name": ["host1", "host2"],
        },
        "options": {},
    },
    {
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
        "value": {
            "hu": "BLA"
        },
        "condition": {
            "host_name": ["xyz"],
        },
        "options": {
            "disabled": True,
        },
    },
]


def test_basic_host_ruleset_get_merged_dict_values(monkeypatch):
    ts = Scenario().add_host("abc")
    ts.add_host("abc")
    ts.add_host("xyz")
    ts.add_host("host1")
    ts.add_host("host2")
    config_cache = ts.apply(monkeypatch)

    matcher = config_cache.ruleset_matcher
    assert matcher.get_host_ruleset_merged_dict(RulesetMatchObject(host_name="abc",
                                                                   service_description=None),
                                                ruleset=dict_ruleset) == {}
    assert matcher.get_host_ruleset_merged_dict(RulesetMatchObject(host_name="xyz",
                                                                   service_description=None),
                                                ruleset=dict_ruleset) == {}
    assert matcher.get_host_ruleset_merged_dict(RulesetMatchObject(host_name="host1",
                                                                   service_description=None),
                                                ruleset=dict_ruleset) == {
                                                    "hu": "BLA",
                                                    "ho": "BLA",
                                                    "he": "BLUB",
                                                }
    assert matcher.get_host_ruleset_merged_dict(RulesetMatchObject(host_name="host2",
                                                                   service_description=None),
                                                ruleset=dict_ruleset) == {
                                                    "hu": "BLUB",
                                                    "ho": "BLA",
                                                    "he": "BLUB",
                                                }


binary_ruleset = [
    {
        "value": True,
        "condition": {
            "host_name": ["host1"],
        },
        "options": {},
    },
    {
        "value": False,
        "condition": {
            "host_name": ["host1", "host2"]
        },
        "options": {},
    },
    {
        "value": True,
        "condition": {
            "host_name": ["host1", "host2"],
        },
        "options": {},
    },
    {
        "value": True,
        "condition": {
            "host_name": ["xyz"],
        },
        "options": {
            "disabled": True,
        },
    },
]


def test_basic_host_ruleset_is_matching_host_ruleset(monkeypatch):
    ts = Scenario().add_host("abc")
    ts.add_host("abc")
    ts.add_host("xyz")
    ts.add_host("host1")
    ts.add_host("host2")
    config_cache = ts.apply(monkeypatch)

    matcher = config_cache.ruleset_matcher
    assert matcher.is_matching_host_ruleset(RulesetMatchObject(host_name="abc",
                                                               service_description=None),
                                            ruleset=binary_ruleset) is False
    assert matcher.is_matching_host_ruleset(RulesetMatchObject(host_name="xyz",
                                                               service_description=None),
                                            ruleset=binary_ruleset) is False
    assert matcher.is_matching_host_ruleset(RulesetMatchObject(host_name="host1",
                                                               service_description=None),
                                            ruleset=binary_ruleset) is True
    assert matcher.is_matching_host_ruleset(RulesetMatchObject(host_name="host2",
                                                               service_description=None),
                                            ruleset=binary_ruleset) is False


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
        "condition": {
            "host_tags": {
                "networking": {
                    "$ne": "lan"
                }
            }
        },
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


@pytest.mark.parametrize("hostname,expected_result", [
    ("host1", ["crit_prod", "prod_cmk-agent", "wan_or_lan", "BLA"]),
    ("host2", ["not_lan", "wan_or_lan", "BLA"]),
    ("host3", ["not_lan", "not_wan_and_not_lan", "BLA"]),
])
def test_ruleset_matcher_get_host_ruleset_values_tags(monkeypatch, hostname, expected_result):
    ts = Scenario()
    ts.add_host("host1", tags={
        "criticality": "prod",
        "agent": "cmk-agent",
        "networking": "lan",
    })
    ts.add_host("host2", tags={
        "criticality": "test",
        "networking": "wan",
    })
    ts.add_host("host3", tags={
        "criticality": "test",
        "networking": "dmz",
    })
    config_cache = ts.apply(monkeypatch)
    matcher = config_cache.ruleset_matcher

    assert list(
        matcher.get_host_ruleset_values(RulesetMatchObject(host_name=hostname,
                                                           service_description=None),
                                        ruleset=tag_ruleset,
                                        is_binary=False)) == expected_result


service_label_ruleset = [
    # test simple label match
    {
        "value": "os_linux",
        "condition": {
            "service_labels": {
                u"os": u"linux",
            },
        },
        "options": {},
    },
    # test implicit AND and unicode value match
    {
        "value": "abc",
        "condition": {
            "service_labels": {
                u"os": u"linux",
                u"abc": u"xä",
            },
        },
        "options": {},
    },
    # test negation of label
    {
        "value": "hu",
        "condition": {
            "service_labels": {
                u"hu": {
                    "$ne": u"ha"
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


@pytest.mark.parametrize("hostname,service_description,expected_result", [
    ("host1", "CPU load", ["os_linux", "abc", "BLA"]),
    ("host2", "CPU load", ["hu", "BLA"]),
])
def test_ruleset_matcher_get_service_ruleset_values_labels(monkeypatch, hostname,
                                                           service_description, expected_result):
    ts = Scenario()

    ts.add_host("host1")
    ts.set_autochecks("host1", [
        Service(CheckPluginName("cpu_load"),
                None,
                "CPU load",
                "{}",
                service_labels=DiscoveredServiceLabels(
                    ServiceLabel(u"os", u"linux"),
                    ServiceLabel(u"abc", u"xä"),
                    ServiceLabel(u"hu", u"ha"),
                ))
    ])

    ts.add_host("host2")
    ts.set_autochecks("host2", [
        Service(
            CheckPluginName("cpu_load"),
            None,
            "CPU load",
            "{}",
            service_labels=DiscoveredServiceLabels(),
        ),
    ])

    config_cache = ts.apply(monkeypatch)
    matcher = config_cache.ruleset_matcher

    assert list(
        matcher.get_service_ruleset_values(config_cache.ruleset_match_object_of_service(
            hostname, service_description),
                                           ruleset=service_label_ruleset,
                                           is_binary=False)) == expected_result


def test_ruleset_optimizer_clear_ruleset_caches(monkeypatch):
    config_cache = Scenario().apply(monkeypatch)
    ruleset_optimizer = config_cache.ruleset_matcher.ruleset_optimizer
    ruleset_optimizer.get_service_ruleset(ruleset, False, False)
    ruleset_optimizer.get_host_ruleset(ruleset, False, False)
    assert ruleset_optimizer._host_ruleset_cache
    assert ruleset_optimizer._service_ruleset_cache
    ruleset_optimizer.clear_ruleset_caches()
    assert not ruleset_optimizer._host_ruleset_cache
    assert not ruleset_optimizer._service_ruleset_cache
