#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

import cmk.base.discovery as discovery
from cmk.base.discovered_labels import ServiceLabel, DiscoveredServiceLabels
import cmk.base.config as config


def test_discovered_service_init():
    s = discovery.DiscoveredService("abc", u"Item", u"ABC Item", "None")
    assert s.check_plugin_name == "abc"
    assert s.item == u"Item"
    assert s.description == u"ABC Item"
    assert s.parameters_unresolved == "None"
    assert s.service_labels.to_dict() == {}

    s = discovery.DiscoveredService("abc", u"Item", u"ABC Item", "None",
                                    DiscoveredServiceLabels(ServiceLabel(u"läbel", u"lübel")))
    assert s.service_labels.to_dict() == {u"läbel": u"lübel"}

    with pytest.raises(AttributeError):
        s.xyz = "abc"  # type: ignore[attr-defined] # pylint: disable=assigning-non-slot


def test_discovered_service_eq():
    s1 = discovery.DiscoveredService("abc", u"Item", u"ABC Item", "None")
    s2 = discovery.DiscoveredService("abc", u"Item", u"ABC Item", "None")
    s3 = discovery.DiscoveredService("xyz", u"Item", u"ABC Item", "None")
    s4 = discovery.DiscoveredService("abc", u"Xtem", u"ABC Item", "None")
    s5 = discovery.DiscoveredService("abc", u"Item", u"ABC Item", "[]")

    assert s1 == s1  # pylint: disable=comparison-with-itself
    assert s1 == s2
    assert s1 != s3
    assert s1 != s4
    assert s1 == s5

    assert s1 in [s1]
    assert s1 in [s2]
    assert s1 not in [s3]
    assert s1 not in [s4]
    assert s1 in [s5]

    assert s1 in {s1}
    assert s1 in {s2}
    assert s1 not in {s3}
    assert s1 not in {s4}
    assert s1 in {s5}


@pytest.mark.parametrize("parameters_rediscovery", [
    {},
    {
        "service_whitelist": [],
    },
    {
        "service_blacklist": [],
    },
    {
        "service_whitelist": [],
        "service_blacklist": [],
    },
])
def test__get_item_filter_func_no_lists(parameters_rediscovery):
    assert discovery._get_item_filter_func(parameters_rediscovery) is None


@pytest.mark.parametrize("whitelist, result", [
    (["^Test"], True),
    (["^test"], False),
    ([".*Description"], True),
    ([".*Descript$"], False),
])
def test__get_item_filter_func_same_lists(monkeypatch, whitelist, result):
    monkeypatch.setattr(config, "service_description", lambda h, c, i: "Test Description")

    item_filter_func = discovery._get_item_filter_func({"service_whitelist": whitelist})
    assert item_filter_func is not None
    assert item_filter_func("hostname", "check_plugin_name", "item") is result

    item_filter_func_inverse = discovery._get_item_filter_func({"service_blacklist": whitelist})
    assert item_filter_func_inverse is not None
    assert item_filter_func_inverse("hostname", "check_plugin_name", "item") is not result

    item_filter_func_both = discovery._get_item_filter_func({
        "service_whitelist": whitelist,
        "service_blacklist": whitelist,
    })
    assert item_filter_func_both is not None
    assert item_filter_func_both("hostname", "check_plugin_name", "item") is False


@pytest.mark.parametrize(
    "params_rediscovery, result",
    [
        (
            {
                # Matches
                "service_whitelist": ["^Test"],
                # Does not match
                "service_blacklist": [".*Descript$"],
            },
            True),
        (
            {
                # Matches
                "service_whitelist": ["^Test"],
                # Matches
                "service_blacklist": [".*Description$"],
            },
            False),
        (
            {
                # Does not match
                "service_whitelist": ["^test"],
                # Matches
                "service_blacklist": [".*Description$"],
            },
            False),
        (
            {
                # Does not match
                "service_whitelist": ["^test"],
                # Does not match
                "service_blacklist": [".*Descript$"],
            },
            False),
    ])
def test__get_item_filter_func(monkeypatch, params_rediscovery, result):
    monkeypatch.setattr(config, "service_description", lambda h, c, i: "Test Description")

    item_filter_func = discovery._get_item_filter_func(params_rediscovery)
    assert item_filter_func is not None
    assert item_filter_func("hostname", "check_plugin_name", "item") is result
    #https://review.lan.tribe29.com/c/check_mk/+/1422/1/cmk_base/discovery.py
