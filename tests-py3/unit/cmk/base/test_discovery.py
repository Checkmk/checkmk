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
def test__get_service_filter_func_no_lists(parameters_rediscovery):
    assert discovery._get_service_filter_func(
        parameters_rediscovery) is discovery._accept_all_services


@pytest.mark.parametrize("whitelist, result", [
    (["^Test"], True),
    (["^test"], False),
    ([".*Description"], True),
    ([".*Descript$"], False),
])
def test__get_service_filter_func_same_lists(monkeypatch, whitelist, result):
    monkeypatch.setattr(config, "service_description", lambda h, c, i: "Test Description")

    service_filter = discovery._get_service_filter_func({"service_whitelist": whitelist})
    assert service_filter is not None
    assert service_filter("hostname", "check_plugin_name", "item") is result

    service_filter_inverse = discovery._get_service_filter_func({"service_blacklist": whitelist})
    assert service_filter_inverse is not None
    assert service_filter_inverse("hostname", "check_plugin_name", "item") is not result

    service_filter_both = discovery._get_service_filter_func({
        "service_whitelist": whitelist,
        "service_blacklist": whitelist,
    })
    assert service_filter_both is not None
    assert service_filter_both("hostname", "check_plugin_name", "item") is False


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
def test__get_service_filter_func(monkeypatch, params_rediscovery, result):
    monkeypatch.setattr(config, "service_description", lambda h, c, i: "Test Description")

    service_filter = discovery._get_service_filter_func(params_rediscovery)
    assert service_filter is not None
    assert service_filter("hostname", "check_plugin_name", "item") is result


@pytest.mark.parametrize(
    "mode, parameters_rediscovery, result_new_item_names, result_counts",
    [
        # No params
        ("new", {}, ["New Item 1", "New Item 2", "Vanished Item 1", "Vanished Item 2"], (2, 2, 0)),
        ("fixall", {}, ["New Item 1", "New Item 2"], (2, 0, 2)),
        ("refresh", {}, ["New Item 1", "New Item 2", "Vanished Item 1", "Vanished Item 2"],
         (2, 2, 0)),
        ("remove", {}, [], (0, 0, 2)),
        # New services
        # Whitelist
        ("new", {
            "service_whitelist": ["^Test Description New Item 1"]
        }, ["New Item 1", "Vanished Item 1", "Vanished Item 2"], (1, 2, 0)),
        ("fixall", {
            "service_whitelist": ["^Test Description New Item 1"]
        }, ["New Item 1", "Vanished Item 1", "Vanished Item 2"], (1, 2, 0)),
        ("refresh", {
            "service_whitelist": ["^Test Description New Item 1"]
        }, ["New Item 1", "Vanished Item 1", "Vanished Item 2"], (1, 2, 0)),
        ("remove", {
            "service_whitelist": ["^Test Description New Item 1"]
        }, ["Vanished Item 1", "Vanished Item 2"], (0, 2, 0)),
        # Blacklist
        ("new", {
            "service_blacklist": ["^Test Description New Item 1"]
        }, ["New Item 2", "Vanished Item 1", "Vanished Item 2"], (1, 2, 0)),
        ("fixall", {
            "service_blacklist": ["^Test Description New Item 1"]
        }, ["New Item 2"], (1, 0, 2)),
        ("refresh", {
            "service_blacklist": ["^Test Description New Item 1"]
        }, ["New Item 2", "Vanished Item 1", "Vanished Item 2"], (1, 2, 0)),
        ("remove", {
            "service_blacklist": ["^Test Description New Item 1"]
        }, [], (0, 0, 2)),
        # White-/blacklist
        ("new", {
            "service_whitelist": ["^Test Description New Item 1"],
            "service_blacklist": ["^Test Description New Item 2"],
        }, ["New Item 1", "Vanished Item 1", "Vanished Item 2"], (1, 2, 0)),
        ("fixall", {
            "service_whitelist": ["^Test Description New Item 1"],
            "service_blacklist": ["^Test Description New Item 2"],
        }, ["New Item 1", "Vanished Item 1", "Vanished Item 2"], (1, 2, 0)),
        ("refresh", {
            "service_whitelist": ["^Test Description New Item 1"],
            "service_blacklist": ["^Test Description New Item 2"],
        }, ["New Item 1", "Vanished Item 1", "Vanished Item 2"], (1, 2, 0)),
        ("remove", {
            "service_whitelist": ["^Test Description New Item 1"],
            "service_blacklist": ["^Test Description New Item 2"],
        }, ["Vanished Item 1", "Vanished Item 2"], (0, 2, 0)),
        # Vanished services
        # Whitelist
        ("new", {
            "service_whitelist": ["^Test Description Vanished Item 1"]
        }, ["Vanished Item 1", "Vanished Item 2"], (0, 2, 0)),
        ("fixall", {
            "service_whitelist": ["^Test Description Vanished Item 1"]
        }, ["Vanished Item 2"], (0, 1, 1)),
        ("refresh", {
            "service_whitelist": ["^Test Description Vanished Item 1"]
        }, ["Vanished Item 1", "Vanished Item 2"], (0, 2, 0)),
        ("remove", {
            "service_whitelist": ["^Test Description Vanished Item 1"]
        }, ["Vanished Item 2"], (0, 1, 1)),
        # Blacklist
        ("new", {
            "service_blacklist": ["^Test Description Vanished Item 1"]
        }, ["New Item 1", "New Item 2", "Vanished Item 1", "Vanished Item 2"], (2, 2, 0)),
        ("fixall", {
            "service_blacklist": ["^Test Description Vanished Item 1"]
        }, ["New Item 1", "New Item 2", "Vanished Item 1"], (2, 1, 1)),
        ("refresh", {
            "service_blacklist": ["^Test Description Vanished Item 1"]
        }, ["New Item 1", "New Item 2", "Vanished Item 1", "Vanished Item 2"], (2, 2, 0)),
        ("remove", {
            "service_blacklist": ["^Test Description Vanished Item 1"]
        }, ["Vanished Item 1"], (0, 1, 1)),
        # White-/blacklist
        ("new", {
            "service_whitelist": ["^Test Description Vanished Item 1"],
            "service_blacklist": ["^Test Description Vanished Item 2"],
        }, ["Vanished Item 1", "Vanished Item 2"], (0, 2, 0)),
        ("fixall", {
            "service_whitelist": ["^Test Description Vanished Item 1"],
            "service_blacklist": ["^Test Description Vanished Item 2"],
        }, ["Vanished Item 2"], (0, 1, 1)),
        ("refresh", {
            "service_whitelist": ["^Test Description Vanished Item 1"],
            "service_blacklist": ["^Test Description Vanished Item 2"],
        }, ["Vanished Item 1", "Vanished Item 2"], (0, 2, 0)),
        ("remove", {
            "service_whitelist": ["^Test Description Vanished Item 1"],
            "service_blacklist": ["^Test Description Vanished Item 2"],
        }, ["Vanished Item 2"], (0, 1, 1)),
    ])
def test__get_new_services(monkeypatch, mode, parameters_rediscovery, result_new_item_names,
                           result_counts):
    def _get_service_description(_hostname, _check_plugin_name, item):
        return "Test Description %s" % item

    monkeypatch.setattr(config, "service_description", _get_service_description)

    counts = discovery._empty_counts()

    service_table = {
        ("check_plugin_name", "New Item 1"):
            ("new",
             discovery.DiscoveredService("check_plugin_name", "New Item 1",
                                         "Test Description New Item 1", "{}")),
        ("check_plugin_name", "New Item 2"):
            ("new",
             discovery.DiscoveredService("check_plugin_name", "New Item 2",
                                         "Test Description New Item 2", "{}")),
        ("check_plugin_name", "Vanished Item 1"):
            ("vanished",
             discovery.DiscoveredService("check_plugin_name", "Vanished Item 1",
                                         "Test Description Vanished Item 1", "{}")),
        ("check_plugin_name", "Vanished Item 2"):
            ("vanished",
             discovery.DiscoveredService("check_plugin_name", "Vanished Item 2",
                                         "Test Description Vanished Item 2", "{}")),
    }  # type: discovery.ServicesTable

    service_filter = discovery._get_service_filter_func(parameters_rediscovery)

    new_item_names = [
        entry.item for entry in discovery._get_new_services(
            "hostname",
            service_table,
            service_filter,
            counts,
            mode,
        )
    ]

    count_new, count_kept, count_removed = result_counts

    assert sorted(new_item_names) == sorted(result_new_item_names)
    assert counts["self_new"] == count_new
    assert counts["self_kept"] == count_kept
    assert counts["self_removed"] == count_removed
