#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name,protected-access

import pytest  # type: ignore[import]
from typing import Dict, Set, NamedTuple, Counter

# No stub files
from testlib.base import Scenario  # type: ignore[import]
from testlib.debug_utils import cmk_debug_enabled  # type: ignore[import]

from cmk.utils.type_defs import CheckPluginName, SectionName, SourceType
from cmk.utils.labels import DiscoveredHostLabelsStore

import cmk.base.ip_lookup as ip_lookup
from cmk.base.checkers.agent import AgentHostSections
from cmk.base.checkers.snmp import SNMPHostSections
from cmk.base.checkers.host_sections import HostKey, MultiHostSections
from cmk.base.discovered_labels import (
    ServiceLabel,
    DiscoveredServiceLabels,
    DiscoveredHostLabels,
    HostLabel,
)

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
import cmk.base.discovery as discovery
import cmk.base.autochecks as autochecks


def test_discovered_service_init():
    ser = discovery.Service(CheckPluginName("abc"), u"Item", u"ABC Item", None)
    assert ser.check_plugin_name == CheckPluginName("abc")
    assert ser.item == u"Item"
    assert ser.description == u"ABC Item"
    assert ser.parameters is None
    assert ser.service_labels.to_dict() == {}

    ser = discovery.Service(CheckPluginName("abc"), u"Item", u"ABC Item", None,
                            DiscoveredServiceLabels(ServiceLabel(u"läbel", u"lübel")))
    assert ser.service_labels.to_dict() == {u"läbel": u"lübel"}

    with pytest.raises(AttributeError):
        ser.xyz = "abc"  # type: ignore[attr-defined] # pylint: disable=assigning-non-slot


def test_discovered_service_eq():
    ser1 = discovery.Service(CheckPluginName("abc"), u"Item", u"ABC Item", None)
    ser2 = discovery.Service(CheckPluginName("abc"), u"Item", u"ABC Item", None)
    ser3 = discovery.Service(CheckPluginName("xyz"), u"Item", u"ABC Item", None)
    ser4 = discovery.Service(CheckPluginName("abc"), u"Xtem", u"ABC Item", None)
    ser5 = discovery.Service(CheckPluginName("abc"), u"Item", u"ABC Item", [])

    assert ser1 == ser1  # pylint: disable=comparison-with-itself
    assert ser1 == ser2
    assert ser1 != ser3
    assert ser1 != ser4
    assert ser1 == ser5

    assert ser1 in [ser1]
    assert ser1 in [ser2]
    assert ser1 not in [ser3]
    assert ser1 not in [ser4]
    assert ser1 in [ser5]

    assert ser1 in {ser1}
    assert ser1 in {ser2}
    assert ser1 not in {ser3}
    assert ser1 not in {ser4}
    assert ser1 in {ser5}


def test__get_rediscovery_mode():
    allowed_modes = [
        ("fixall", 2),
        ("new", 0),
        ("refresh", 3),
        ("remove", 1),
    ]

    assert sorted(allowed_modes) == sorted(
        (member.name, member.value) for member in discovery.RediscoveryMode)
    assert discovery._get_rediscovery_mode({}) == ""
    assert discovery._get_rediscovery_mode({"inventory_rediscovery": {}}) == ""
    assert discovery._get_rediscovery_mode({"inventory_rediscovery": {"mode": "UNKNOWN"}}) == ""


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
    {
        "vanished_service_whitelist": [],
    },
    {
        "vanished_service_blacklist": [],
    },
    {
        "vanished_service_whitelist": [],
        "vanished_service_blacklist": [],
    },
])
def test__get_service_filter_func_no_lists(parameters_rediscovery):
    params = {"inventory_rediscovery": parameters_rediscovery}
    service_filters = discovery.get_service_filter_funcs(params)
    assert service_filters.new is discovery._accept_all_services
    assert service_filters.vanished is discovery._accept_all_services


@pytest.mark.parametrize("whitelist, result", [
    (["^Test"], True),
    (["^test"], False),
    ([".*Description"], True),
    ([".*Descript$"], False),
])
def test__get_service_filter_func_same_lists(monkeypatch, whitelist, result):
    monkeypatch.setattr(config, "service_description", lambda h, c, i: "Test Description")

    params = {"inventory_rediscovery": {"service_whitelist": whitelist}}
    service_filters = discovery.get_service_filter_funcs(params)
    service = discovery.Service(CheckPluginName("check_plugin_name"), "item", "Test Description",
                                None)
    assert service_filters.new is not None
    assert service_filters.new("hostname", service) is result

    params = {"inventory_rediscovery": {"service_blacklist": whitelist}}
    service_filters_inverse = discovery.get_service_filter_funcs(params)
    assert service_filters_inverse.new is not None
    assert service_filters_inverse.new("hostname", service) is not result

    params = {
        "inventory_rediscovery": {
            "service_whitelist": whitelist,
            "service_blacklist": whitelist,
        }
    }
    service_filters_both = discovery.get_service_filter_funcs(params)
    assert service_filters_both.new is not None
    assert service_filters_both.new("hostname", service) is False


@pytest.mark.parametrize(
    "parameters_rediscovery, result",
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
def test__get_service_filter_func(monkeypatch, parameters_rediscovery, result):
    monkeypatch.setattr(config, "service_description", lambda h, c, i: "Test Description")

    params = {"inventory_rediscovery": parameters_rediscovery}
    service_filters = discovery.get_service_filter_funcs(params)
    service = discovery.Service(CheckPluginName("check_plugin_name"), "item", "Test Description",
                                None)
    assert service_filters.new is not None
    assert service_filters.new("hostname", service) is result


@pytest.fixture
def service_table() -> discovery.ServicesTable:
    return {
        (CheckPluginName("check_plugin_name"), "New Item 1"): (
            "new",
            discovery.Service(
                CheckPluginName("check_plugin_name"),
                "New Item 1",
                "Test Description New Item 1",
                {},
            ),
        ),
        (CheckPluginName("check_plugin_name"), "New Item 2"): (
            "new",
            discovery.Service(
                CheckPluginName("check_plugin_name"),
                "New Item 2",
                "Test Description New Item 2",
                {},
            ),
        ),
        (CheckPluginName("check_plugin_name"), "Vanished Item 1"): (
            "vanished",
            discovery.Service(
                CheckPluginName("check_plugin_name"),
                "Vanished Item 1",
                "Test Description Vanished Item 1",
                {},
            ),
        ),
        (CheckPluginName("check_plugin_name"), "Vanished Item 2"): (
            "vanished",
            discovery.Service(
                CheckPluginName("check_plugin_name"),
                "Vanished Item 2",
                "Test Description Vanished Item 2",
                {},
            ),
        ),
    }


@pytest.fixture
def grouped_services() -> discovery.ServicesByTransition:
    return {
        "new": [
            discovery.Service(
                CheckPluginName("check_plugin_name"),
                "New Item 1",
                "Test Description New Item 1",
                {},
            ),
            discovery.Service(
                CheckPluginName("check_plugin_name"),
                "New Item 2",
                "Test Description New Item 2",
                {},
            ),
        ],
        "vanished": [
            discovery.Service(
                CheckPluginName("check_plugin_name"),
                "Vanished Item 1",
                "Test Description Vanished Item 1",
                {},
            ),
            discovery.Service(
                CheckPluginName("check_plugin_name"),
                "Vanished Item 2",
                "Test Description Vanished Item 2",
                {},
            ),
        ],
    }


def test__group_by_transition(service_table, grouped_services):
    assert discovery._group_by_transition(service_table.values()) == grouped_services


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
def test__get_post_discovery_services(monkeypatch, grouped_services, mode, parameters_rediscovery,
                                      result_new_item_names, result_counts):
    def _get_service_description(_hostname, _check_plugin_name, item):
        return "Test Description %s" % item

    monkeypatch.setattr(config, "service_description", _get_service_description)

    counts = discovery._empty_counts()

    params = {"inventory_rediscovery": parameters_rediscovery}
    service_filters = discovery.get_service_filter_funcs(params)

    new_item_names = [
        entry.item for entry in discovery._get_post_discovery_services(
            "hostname",
            grouped_services,
            service_filters,
            counts,
            mode,
        )
    ]

    count_new, count_kept, count_removed = result_counts

    assert sorted(new_item_names) == sorted(result_new_item_names)
    assert counts["self_new"] == count_new
    assert counts["self_kept"] == count_kept
    assert counts["self_removed"] == count_removed


@pytest.mark.parametrize(
    "parameters, result_need_rediscovery",
    [
        ({}, False),
        # New services
        # Whitelist
        ({
            "inventory_rediscovery": {
                "mode": 0,
                "service_whitelist": ["^Test Description New Item 1"]
            },
        }, True),
        ({
            "inventory_rediscovery": {
                "mode": 1,
                "service_whitelist": ["^Test Description New Item 1"]
            },
        }, False),
        ({
            "inventory_rediscovery": {
                "mode": 2,
                "service_whitelist": ["^Test Description New Item 1"]
            },
        }, True),
        ({
            "inventory_rediscovery": {
                "mode": 3,
                "service_whitelist": ["^Test Description New Item 1"]
            },
        }, True),
        # Blacklist
        ({
            "inventory_rediscovery": {
                "mode": 0,
                "service_blacklist": ["^Test Description New Item 1"]
            },
        }, True),
        ({
            "inventory_rediscovery": {
                "mode": 1,
                "service_blacklist": ["^Test Description New Item 1"]
            },
        }, True),
        ({
            "inventory_rediscovery": {
                "mode": 2,
                "service_blacklist": ["^Test Description New Item 1"]
            },
        }, True),
        ({
            "inventory_rediscovery": {
                "mode": 3,
                "service_blacklist": ["^Test Description New Item 1"]
            },
        }, True),
        # White-/blacklist
        ({
            "inventory_rediscovery": {
                "mode": 0,
                "service_whitelist": ["^Test Description New Item 1"],
                "service_blacklist": ["^Test Description New Item 2"],
            },
        }, True),
        ({
            "inventory_rediscovery": {
                "mode": 1,
                "service_whitelist": ["^Test Description New Item 1"],
                "service_blacklist": ["^Test Description New Item 2"],
            },
        }, False),
        ({
            "inventory_rediscovery": {
                "mode": 2,
                "service_whitelist": ["^Test Description New Item 1"],
                "service_blacklist": ["^Test Description New Item 2"],
            },
        }, True),
        ({
            "inventory_rediscovery": {
                "mode": 3,
                "service_whitelist": ["^Test Description New Item 1"],
                "service_blacklist": ["^Test Description New Item 2"],
            },
        }, True),
        # Vanished services
        # Whitelist
        ({
            "inventory_rediscovery": {
                "mode": 0,
                "service_whitelist": ["^Test Description Vanished Item 1"]
            },
        }, False),
        ({
            "inventory_rediscovery": {
                "mode": 1,
                "service_whitelist": ["^Test Description Vanished Item 1"]
            },
        }, True),
        ({
            "inventory_rediscovery": {
                "mode": 2,
                "service_whitelist": ["^Test Description Vanished Item 1"]
            },
        }, True),
        ({
            "inventory_rediscovery": {
                "mode": 3,
                "service_whitelist": ["^Test Description Vanished Item 1"]
            },
        }, True),
        # Blacklist
        ({
            "inventory_rediscovery": {
                "mode": 0,
                "service_blacklist": ["^Test Description Vanished Item 1"]
            },
        }, True),
        ({
            "inventory_rediscovery": {
                "mode": 1,
                "service_blacklist": ["^Test Description Vanished Item 1"]
            },
        }, True),
        ({
            "inventory_rediscovery": {
                "mode": 2,
                "service_blacklist": ["^Test Description Vanished Item 1"]
            },
        }, True),
        ({
            "inventory_rediscovery": {
                "mode": 3,
                "service_blacklist": ["^Test Description Vanished Item 1"]
            },
        }, True),
        # White-/blacklist
        ({
            "inventory_rediscovery": {
                "mode": 0,
                "service_whitelist": ["^Test Description Vanished Item 1"],
                "service_blacklist": ["^Test Description Vanished Item 2"],
            },
        }, False),
        ({
            "inventory_rediscovery": {
                "mode": 1,
                "service_whitelist": ["^Test Description Vanished Item 1"],
                "service_blacklist": ["^Test Description Vanished Item 2"],
            },
        }, True),
        ({
            "inventory_rediscovery": {
                "mode": 2,
                "service_whitelist": ["^Test Description Vanished Item 1"],
                "service_blacklist": ["^Test Description Vanished Item 2"],
            },
        }, True),
        ({
            "inventory_rediscovery": {
                "mode": 3,
                "service_whitelist": ["^Test Description Vanished Item 1"],
                "service_blacklist": ["^Test Description Vanished Item 2"],
            },
        }, True),
    ])
def test__check_service_table(monkeypatch, grouped_services, parameters, result_need_rediscovery):
    def _get_service_description(_hostname, _check_plugin_name, item):
        return "Test Description %s" % item

    monkeypatch.setattr(config, "service_description", _get_service_description)

    status, infotexts, long_infotexts, perfdata, need_rediscovery = discovery._check_service_lists(
        "hostname", grouped_services, parameters)

    assert status == 1
    assert sorted(infotexts) == sorted([
        '2 unmonitored services (check_plugin_name:2)(!)',
        '2 vanished services (check_plugin_name:2)',
    ])
    assert sorted(long_infotexts) == sorted([
        'unmonitored: check_plugin_name: Test Description New Item 1',
        'unmonitored: check_plugin_name: Test Description New Item 2',
        'vanished: check_plugin_name: Test Description Vanished Item 1',
        'vanished: check_plugin_name: Test Description Vanished Item 2',
    ])
    assert perfdata == []
    assert need_rediscovery == result_need_rediscovery


@pytest.mark.parametrize(
    "parameters, new_whitelist, new_blacklist, vanished_whitelist, vanished_blacklist", [
        ({}, None, None, None, None),
        ({
            "inventory_rediscovery": {}
        }, None, None, None, None),
        ({
            "inventory_rediscovery": {
                "service_whitelist": ["white"],
            }
        }, ["white"], None, ["white"], None),
        ({
            "inventory_rediscovery": {
                "service_blacklist": ["black"],
            }
        }, None, ["black"], None, ["black"]),
        ({
            "inventory_rediscovery": {
                "service_whitelist": ["white"],
                "service_blacklist": ["black"],
            }
        }, ["white"], ["black"], ["white"], ["black"]),
        ({
            "inventory_rediscovery": {
                "service_filters": ("combined", {}),
            }
        }, None, None, None, None),
        ({
            "inventory_rediscovery": {
                "service_filters": ("combined", {
                    "service_whitelist": ["white"],
                }),
            }
        }, ["white"], None, ["white"], None),
        ({
            "inventory_rediscovery": {
                "service_filters": ("combined", {
                    "service_blacklist": ["black"],
                }),
            }
        }, None, ["black"], None, ["black"]),
        ({
            "inventory_rediscovery": {
                "service_filters": ("combined", {
                    "service_whitelist": ["white"],
                    "service_blacklist": ["black"],
                }),
            }
        }, ["white"], ["black"], ["white"], ["black"]),
        ({
            "inventory_rediscovery": {
                "service_filters": ("dedicated", {}),
            }
        }, None, None, None, None),
        ({
            "inventory_rediscovery": {
                "service_filters": ("dedicated", {
                    "service_whitelist": ["white"],
                }),
            }
        }, ["white"], None, None, None),
        ({
            "inventory_rediscovery": {
                "service_filters": ("dedicated", {
                    "service_blacklist": ["black"],
                }),
            }
        }, None, ["black"], None, None),
        ({
            "inventory_rediscovery": {
                "service_filters": ("dedicated", {
                    "service_whitelist": ["white"],
                    "service_blacklist": ["black"],
                }),
            }
        }, ["white"], ["black"], None, None),
        ({
            "inventory_rediscovery": {
                "service_filters": ("dedicated", {
                    "vanished_service_whitelist": ["white"],
                }),
            }
        }, None, None, ["white"], None),
        ({
            "inventory_rediscovery": {
                "service_filters": ("dedicated", {
                    "vanished_service_blacklist": ["black"],
                }),
            }
        }, None, None, None, ["black"]),
        ({
            "inventory_rediscovery": {
                "service_filters": ("dedicated", {
                    "vanished_service_whitelist": ["white"],
                    "vanished_service_blacklist": ["black"],
                }),
            }
        }, None, None, ["white"], ["black"]),
        ({
            "inventory_rediscovery": {
                "service_filters": ("dedicated", {
                    "service_whitelist": ["white_new"],
                    "vanished_service_whitelist": ["white_vanished"],
                }),
            }
        }, ["white_new"], None, ["white_vanished"], None),
        ({
            "inventory_rediscovery": {
                "service_filters": ("dedicated", {
                    "service_whitelist": ["white_new"],
                    "vanished_service_blacklist": ["black_vanished"],
                }),
            }
        }, ["white_new"], None, None, ["black_vanished"]),
        ({
            "inventory_rediscovery": {
                "service_filters": ("dedicated", {
                    "service_blacklist": ["black_new"],
                    "vanished_service_whitelist": ["white_vanished"],
                }),
            }
        }, None, ["black_new"], ["white_vanished"], None),
        ({
            "inventory_rediscovery": {
                "service_filters": ("dedicated", {
                    "service_blacklist": ["black_new"],
                    "vanished_service_blacklist": ["black_vanished"],
                }),
            }
        }, None, ["black_new"], None, ["black_vanished"]),
        ({
            "inventory_rediscovery": {
                "service_filters": ("dedicated", {
                    "service_whitelist": ["white_new"],
                    "service_blacklist": ["black_new"],
                    "vanished_service_whitelist": ["white_vanished"],
                }),
            }
        }, ["white_new"], ["black_new"], ["white_vanished"], None),
        ({
            "inventory_rediscovery": {
                "service_filters": ("dedicated", {
                    "service_whitelist": ["white_new"],
                    "service_blacklist": ["black_new"],
                    "vanished_service_blacklist": ["black_vanished"],
                }),
            }
        }, ["white_new"], ["black_new"], None, ["black_vanished"]),
        ({
            "inventory_rediscovery": {
                "service_filters": ("dedicated", {
                    "service_whitelist": ["white_new"],
                    "service_blacklist": ["black_new"],
                    "vanished_service_whitelist": ["white_vanished"],
                    "vanished_service_blacklist": ["black_vanished"],
                }),
            }
        }, ["white_new"], ["black_new"], ["white_vanished"], ["black_vanished"]),
        ({
            "inventory_rediscovery": {
                "service_filters": ("dedicated", {
                    "service_whitelist": ["white_new"],
                    "vanished_service_whitelist": ["white_vanished"],
                    "vanished_service_blacklist": ["black_vanished"],
                }),
            }
        }, ["white_new"], None, ["white_vanished"], ["black_vanished"]),
        ({
            "inventory_rediscovery": {
                "service_filters": ("dedicated", {
                    "service_blacklist": ["black_new"],
                    "vanished_service_whitelist": ["white_vanished"],
                    "vanished_service_blacklist": ["black_vanished"],
                }),
            }
        }, None, ["black_new"], ["white_vanished"], ["black_vanished"]),
    ])
def test__get_service_filters_lists(parameters, new_whitelist, new_blacklist, vanished_whitelist,
                                    vanished_blacklist):
    service_filter_lists = discovery._get_service_filter_lists(parameters)
    assert service_filter_lists.new_whitelist == new_whitelist
    assert service_filter_lists.new_blacklist == new_blacklist
    assert service_filter_lists.vanished_whitelist == vanished_whitelist
    assert service_filter_lists.vanished_blacklist == vanished_blacklist

    service_filters = discovery.get_service_filter_funcs(parameters)
    assert service_filters.new is not None
    assert service_filters.vanished is not None


@pytest.mark.usefixtures("config_load_all_checks")
def test__find_candidates():
    mhs = MultiHostSections()

    mhs._data = {
        # we just care about the keys here, content set to arbitrary values that can be parsed.
        # section names have been are chosen arbitrarily.
        HostKey("test_node", "1.2.3.4", SourceType.HOST): AgentHostSections({
            SectionName("kernel"): [],  # host only
            SectionName("uptime"): [['123']],  # host & mgmt
        }),
        HostKey("test_node", "1.2.3.4", SourceType.MANAGEMENT): SNMPHostSections({
            # host & mgmt:
            SectionName("uptime"): [['123']],  # type: ignore[dict-item]
            # mgmt only:
            SectionName("liebert_fans"): [[['Fan', '67', 'umin']]],  # type: ignore[dict-item]
            # is already mgmt_ prefixed:
            SectionName("mgmt_snmp_info"): [[['a', 'b', 'c', 'd']]],  # type: ignore[dict-item]
        }),
    }

    preliminary_candidates = list(agent_based_register.iter_all_check_plugins())
    parsed_sections_of_interest = {
        parsed_section_name for plugin in preliminary_candidates
        for parsed_section_name in plugin.sections
    }

    assert discovery._find_host_candidates(
        mhs,
        preliminary_candidates,
        parsed_sections_of_interest,
    ) == {
        CheckPluginName('docker_container_status_uptime'),
        CheckPluginName("kernel"),
        CheckPluginName('kernel_performance'),
        CheckPluginName('kernel_util'),
        CheckPluginName("uptime"),
    }

    assert discovery._find_mgmt_candidates(
        mhs,
        preliminary_candidates,
        parsed_sections_of_interest,
    ) == {
        CheckPluginName('mgmt_docker_container_status_uptime'),
        CheckPluginName("mgmt_liebert_fans"),
        CheckPluginName("mgmt_uptime"),
    }

    assert discovery._find_candidates(
        mhs,
        selected_check_plugins=None,
    ) == {
        CheckPluginName('docker_container_status_uptime'),
        CheckPluginName("kernel"),
        CheckPluginName('kernel_performance'),
        CheckPluginName('kernel_util'),
        CheckPluginName('mgmt_docker_container_status_uptime'),
        CheckPluginName("mgmt_liebert_fans"),
        CheckPluginName("mgmt_uptime"),
        CheckPluginName("uptime"),
    }


_expected_services: Dict = {
    (CheckPluginName('apache_status'), '127.0.0.1:5000'): {},
    (CheckPluginName('apache_status'), '127.0.0.1:5004'): {},
    (CheckPluginName('apache_status'), '127.0.0.1:5007'): {},
    (CheckPluginName('apache_status'), '127.0.0.1:5008'): {},
    (CheckPluginName('apache_status'), '127.0.0.1:5009'): {},
    (CheckPluginName('apache_status'), '::1:80'): {},
    (CheckPluginName('check_mk_agent_update'), None): {},
    (CheckPluginName('cpu_loads'), None): {},
    (CheckPluginName('cpu_threads'), None): {},
    (CheckPluginName('df'), '/'): {},
    (CheckPluginName('df'), '/boot'): {},
    (CheckPluginName('df'), '/boot/efi'): {},
    (CheckPluginName('diskstat'), 'SUMMARY'): {},
    (CheckPluginName('kernel_performance'), None): {},
    (CheckPluginName('kernel_util'), None): {},
    (CheckPluginName('livestatus_status'), 'heute'): {},
    (CheckPluginName('livestatus_status'), 'test1'): {},
    (CheckPluginName('livestatus_status'), 'test2'): {},
    (CheckPluginName('livestatus_status'), 'test3'): {},
    (CheckPluginName('livestatus_status'), 'test_crawl'): {},
    (CheckPluginName('lnx_if'), '2'): {},
    (CheckPluginName('lnx_if'), '3'): {},
    (CheckPluginName('lnx_thermal'), 'Zone 0'): {},
    (CheckPluginName('lnx_thermal'), 'Zone 1'): {},
    (CheckPluginName('logwatch'), '/var/log/auth.log'): {},
    (CheckPluginName('logwatch'), '/var/log/kern.log'): {},
    (CheckPluginName('logwatch'), '/var/log/syslog'): {},
    (CheckPluginName('local'), 'SäMB_Share_flr01'): {},
    (CheckPluginName('mem_linux'), None): {},
    (CheckPluginName('mkeventd_status'), 'heute'): {},
    (CheckPluginName('mkeventd_status'), 'test1'): {},
    (CheckPluginName('mkeventd_status'), 'test2'): {},
    (CheckPluginName('mkeventd_status'), 'test3'): {},
    (CheckPluginName('mkeventd_status'), 'test_crawl'): {},
    (CheckPluginName('mknotifyd'), 'heute'): {},
    (CheckPluginName('mknotifyd'), 'heute_slave_1'): {},
    (CheckPluginName('mknotifyd'), 'test1'): {},
    (CheckPluginName('mknotifyd'), 'test2'): {},
    (CheckPluginName('mknotifyd'), 'test3'): {},
    (CheckPluginName('mknotifyd'), 'test_crawl'): {},
    (CheckPluginName('mounts'), '/'): {},
    (CheckPluginName('mounts'), '/boot'): {},
    (CheckPluginName('mounts'), '/boot/efi'): {},
    (CheckPluginName('ntp_time'), None): {},
    (CheckPluginName('omd_apache'), 'aq'): {},
    (CheckPluginName('omd_apache'), 'heute'): {},
    (CheckPluginName('omd_apache'), 'heute_slave_1'): {},
    (CheckPluginName('omd_apache'), 'onelogin'): {},
    (CheckPluginName('omd_apache'), 'stable'): {},
    (CheckPluginName('omd_apache'), 'stable_slave_1'): {},
    (CheckPluginName('omd_apache'), 'test1'): {},
    (CheckPluginName('omd_apache'), 'test2'): {},
    (CheckPluginName('omd_apache'), 'test3'): {},
    (CheckPluginName('omd_apache'), 'test_crawl'): {},
    (CheckPluginName('omd_status'), 'heute'): {},
    (CheckPluginName('omd_status'), 'test1'): {},
    (CheckPluginName('omd_status'), 'test2'): {},
    (CheckPluginName('omd_status'), 'test3'): {},
    (CheckPluginName('omd_status'), 'test_crawl'): {},
    (CheckPluginName('postfix_mailq'), ''): {},
    (CheckPluginName('postfix_mailq_status'), ''): {},
    (CheckPluginName('tcp_conn_stats'), None): {},
    (CheckPluginName('uptime'), None): {},
}

_expected_host_labels = {
    'cmk/os_family': {
        'plugin_name': 'check_mk',
        'value': 'linux',
    },
}


@pytest.mark.usefixtures("config_load_all_checks")
def test_do_discovery(monkeypatch):
    ts = Scenario().add_host("test-host", ipaddress="127.0.0.1")
    ts.fake_standard_linux_agent_output("test-host")
    ts.apply(monkeypatch)

    with cmk_debug_enabled():
        discovery.do_discovery(arg_hostnames={"test-host"},
                               check_plugin_names=None,
                               arg_only_new=False)

    services = autochecks.parse_autochecks_file("test-host", config.service_description)
    found = {(s.check_plugin_name, s.item): s.service_labels.to_dict() for s in services}
    assert found == _expected_services

    store = DiscoveredHostLabelsStore("test-host")
    assert store.load() == _expected_host_labels


RealHostScenario = NamedTuple("RealHostScenario", [
    ("hostname", str),
    ("ipaddress", str),
    ("multi_host_sections", MultiHostSections),
])


@pytest.fixture(name="realhost_scenario")
def _realhost_scenario(monkeypatch):
    hostname = "test-host"
    ipaddress = "127.0.0.1"
    ts = Scenario().add_host(hostname, ipaddress=ipaddress)
    ts.set_ruleset("inventory_df_rules", [{
        'value': {
            'ignore_fs_types': ['tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660'],
            'never_ignore_mountpoints': ['~.*/omd/sites/[^/]+/tmp$']
        },
        'condition': {
            'host_labels': {
                'cmk/check_mk_server': 'yes'
            }
        }
    }])
    ts.apply(monkeypatch)

    DiscoveredHostLabelsStore(hostname).save({
        'existing_label': {
            'plugin_name': 'foo',
            'value': 'bar',
        },
        'another_label': {
            'plugin_name': 'labels',
            'value': 'true',
        }
    })

    return RealHostScenario(
        hostname,
        ipaddress,
        MultiHostSections(
            data={
                HostKey(hostname=hostname, ipaddress=ipaddress, source_type=SourceType.HOST):
                    AgentHostSections(
                        sections={
                            SectionName("labels"): [[
                                '{"cmk/check_mk_server":"yes"}',
                            ],],
                            SectionName("df"): [
                                [
                                    '/dev/sda1',
                                    'vfat',
                                    '523248',
                                    '3668',
                                    '519580',
                                    '1%',
                                    '/boot/efi',
                                ],
                                [
                                    'tmpfs',
                                    'tmpfs',
                                    '8152916',
                                    '244',
                                    '8152672',
                                    '1%',
                                    '/opt/omd/sites/heute/tmp',
                                ],
                            ],
                        })
            }),
    )


ClusterScenario = NamedTuple("ClusterScenario", [
    ("host_config", config.HostConfig),
    ("ipaddress", str),
    ("multi_host_sections", MultiHostSections),
    ("node1_hostname", str),
    ("node2_hostname", str),
])


@pytest.fixture(name="cluster_scenario")
def _cluster_scenario(monkeypatch):
    hostname = "test-cluster"
    ipaddress = "127.0.0.1"
    node1_hostname = 'test-node1'
    node1_ipaddress = "127.0.0.2"
    node2_hostname = 'test-node2'
    node2_ipaddress = "127.0.0.3"

    ipaddresses = {
        hostname: ipaddress,
        node1_hostname: node1_ipaddress,
        node2_hostname: node2_ipaddress,
    }

    def fake_lookup_ip_address(host_config, family=None, for_mgmt_board=True):
        return ipaddresses.get(host_config.hostname)

    monkeypatch.setattr(ip_lookup, "lookup_ip_address", fake_lookup_ip_address)

    ts = Scenario()
    ts.add_host(node1_hostname)
    ts.add_host(node2_hostname)
    ts.add_cluster(hostname, nodes=[node1_hostname, node2_hostname])
    ts.set_ruleset("inventory_df_rules", [{
        'value': {
            'ignore_fs_types': ['tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660'],
            'never_ignore_mountpoints': ['~.*/omd/sites/[^/]+/tmp$']
        },
        'condition': {
            'host_labels': {
                'cmk/check_mk_server': 'yes'
            }
        }
    }])
    ts.set_ruleset("clustered_services", [([], [node1_hostname], ['fs_'])])
    config_cache = ts.apply(monkeypatch)
    host_config = config_cache.get_host_config(hostname)

    DiscoveredHostLabelsStore(node1_hostname).save(
        {'node1_existing_label': {
            'plugin_name': 'node1_plugin',
            'value': 'true',
        }})

    DiscoveredHostLabelsStore(hostname).save({
        'existing_label': {
            'plugin_name': 'foo',
            'value': 'bar',
        },
        'another_label': {
            'plugin_name': 'labels',
            'value': 'true',
        }
    })

    return ClusterScenario(
        host_config,
        ipaddress,
        MultiHostSections(
            data={
                HostKey(hostname=node1_hostname,
                        ipaddress=node1_ipaddress,
                        source_type=SourceType.HOST): AgentHostSections(
                    sections={
                        SectionName("labels"): [[
                            '{"cmk/check_mk_server":"yes"}',
                        ],],
                        SectionName("df"): [
                            [
                                '/dev/sda1',
                                'vfat',
                                '523248',
                                '3668',
                                '519580',
                                '1%',
                                '/boot/efi',
                            ],
                            [
                                'tmpfs',
                                'tmpfs',
                                '8152916',
                                '244',
                                '8152672',
                                '1%',
                                '/opt/omd/sites/heute1/tmp',
                            ],
                        ],
                    }),
                HostKey(hostname=node2_hostname,
                        ipaddress=node2_ipaddress,
                        source_type=SourceType.HOST): AgentHostSections(
                    sections={
                        SectionName("labels"): [[
                            '{"node2_live_label":"true"}',
                        ],],
                        SectionName("df"): [
                            [
                                '/dev/sda1',
                                'vfat',
                                '523248',
                                '3668',
                                '519580',
                                '1%',
                                '/boot/efi',
                            ],
                            [
                                'tmpfs',
                                'tmpfs',
                                '8152916',
                                '244',
                                '8152672',
                                '1%',
                                '/opt/omd/sites/heute2/tmp',
                            ],
                        ],
                    }),
            }),
        node1_hostname,
        node2_hostname,
    )


ExpectedDiscoveryResultRealHost = NamedTuple("ExpectedDiscoveryResultRealHost", [
    ("expected_return_labels", DiscoveredHostLabels),
    ("expected_stored_labels", Dict),
])

ExpectedDiscoveryResultCluster = NamedTuple("ExpectedDiscoveryResultCluster", [
    ("expected_return_labels", DiscoveredHostLabels),
    ("expected_stored_labels_cluster", Dict),
    ("expected_stored_labels_node1", Dict),
    ("expected_stored_labels_node2", Dict),
])

DiscoveryTestCase = NamedTuple("DiscoveryTestCase", [
    ("parameters", discovery.DiscoveryParameters),
    ("on_realhost", ExpectedDiscoveryResultRealHost),
    ("on_cluster", ExpectedDiscoveryResultCluster),
])

_discovery_test_cases = [
    # do discovery: only_new == True
    # discover on host: mode != "remove"
    DiscoveryTestCase(
        parameters=discovery.DiscoveryParameters(
            on_error="raise",
            load_labels=True,
            save_labels=True,
        ),
        on_realhost=ExpectedDiscoveryResultRealHost(
            expected_return_labels=DiscoveredHostLabels(
                HostLabel('cmk/check_mk_server', 'yes', plugin_name='labels'),
                HostLabel('another_label', 'true', plugin_name='labels'),
                HostLabel('existing_label', 'bar', plugin_name='foo'),
            ),
            expected_stored_labels={
                'another_label': {
                    'plugin_name': 'labels',
                    'value': 'true',
                },
                'existing_label': {
                    'plugin_name': 'foo',
                    'value': 'bar',
                },
                'cmk/check_mk_server': {
                    'plugin_name': 'labels',
                    'value': 'yes',
                },
            },
        ),
        on_cluster=ExpectedDiscoveryResultCluster(
            expected_return_labels=DiscoveredHostLabels(
                HostLabel('cmk/check_mk_server', 'yes', plugin_name='labels'),
                HostLabel('existing_label', 'bar', plugin_name='foo'),
                HostLabel('another_label', 'true', plugin_name='labels'),
                HostLabel('node2_live_label', 'true', plugin_name='labels'),
            ),
            expected_stored_labels_cluster={
                'another_label': {
                    'plugin_name': 'labels',
                    'value': 'true',
                },
                'existing_label': {
                    'plugin_name': 'foo',
                    'value': 'bar',
                },
                'cmk/check_mk_server': {
                    'plugin_name': 'labels',
                    'value': 'yes',
                },
                'node2_live_label': {
                    'plugin_name': 'labels',
                    'value': 'true',
                },
            },
            expected_stored_labels_node1={
                'node1_existing_label': {
                    'plugin_name': 'node1_plugin',
                    'value': 'true',
                },
            },
            expected_stored_labels_node2={},
        ),
    ),
    # check discovery
    DiscoveryTestCase(
        parameters=discovery.DiscoveryParameters(
            on_error="raise",
            load_labels=True,
            save_labels=False,
        ),
        on_realhost=ExpectedDiscoveryResultRealHost(
            expected_return_labels=DiscoveredHostLabels(
                HostLabel('cmk/check_mk_server', 'yes', plugin_name='labels'),
                HostLabel('another_label', 'true', plugin_name='labels'),
                HostLabel('existing_label', 'bar', plugin_name='foo'),
            ),
            expected_stored_labels={
                'another_label': {
                    'plugin_name': 'labels',
                    'value': 'true',
                },
                'existing_label': {
                    'plugin_name': 'foo',
                    'value': 'bar',
                },
            },
        ),
        on_cluster=ExpectedDiscoveryResultCluster(
            expected_return_labels=DiscoveredHostLabels(
                HostLabel('cmk/check_mk_server', 'yes', plugin_name='labels'),
                HostLabel('existing_label', 'bar', plugin_name='foo'),
                HostLabel('another_label', 'true', plugin_name='labels'),
                HostLabel('node2_live_label', 'true', plugin_name='labels'),
            ),
            expected_stored_labels_cluster={
                'another_label': {
                    'plugin_name': 'labels',
                    'value': 'true',
                },
                'existing_label': {
                    'plugin_name': 'foo',
                    'value': 'bar',
                },
            },
            expected_stored_labels_node1={
                'node1_existing_label': {
                    'plugin_name': 'node1_plugin',
                    'value': 'true',
                },
            },
            expected_stored_labels_node2={},
        ),
    ),
    # do discovery: only_new == False
    DiscoveryTestCase(
        parameters=discovery.DiscoveryParameters(
            on_error="raise",
            load_labels=False,
            save_labels=True,
        ),
        on_realhost=ExpectedDiscoveryResultRealHost(
            expected_return_labels=DiscoveredHostLabels(
                HostLabel('cmk/check_mk_server', 'yes', plugin_name='labels'),),
            expected_stored_labels={
                'cmk/check_mk_server': {
                    'plugin_name': 'labels',
                    'value': 'yes',
                },
            },
        ),
        on_cluster=ExpectedDiscoveryResultCluster(
            expected_return_labels=DiscoveredHostLabels(
                HostLabel('cmk/check_mk_server', 'yes', plugin_name='labels'),
                HostLabel('node2_live_label', 'true', plugin_name='labels'),
            ),
            expected_stored_labels_cluster={
                'cmk/check_mk_server': {
                    'plugin_name': 'labels',
                    'value': 'yes',
                },
                'node2_live_label': {
                    'plugin_name': 'labels',
                    'value': 'true',
                },
            },
            expected_stored_labels_node1={
                'node1_existing_label': {
                    'plugin_name': 'node1_plugin',
                    'value': 'true',
                },
            },
            expected_stored_labels_node2={},
        ),
    ),
    # discover on host: mode == "remove"
    # do discovery: only_new == False
    # preview
    DiscoveryTestCase(
        parameters=discovery.DiscoveryParameters(
            on_error="raise",
            load_labels=False,
            save_labels=False,
        ),
        on_realhost=ExpectedDiscoveryResultRealHost(
            expected_return_labels=DiscoveredHostLabels(
                HostLabel('cmk/check_mk_server', 'yes', plugin_name='labels'),),
            expected_stored_labels={
                'another_label': {
                    'plugin_name': 'labels',
                    'value': 'true',
                },
                'existing_label': {
                    'plugin_name': 'foo',
                    'value': 'bar',
                },
            },
        ),
        on_cluster=ExpectedDiscoveryResultCluster(
            expected_return_labels=DiscoveredHostLabels(
                HostLabel('cmk/check_mk_server', 'yes', plugin_name='labels'),
                HostLabel('node2_live_label', 'true', plugin_name='labels'),
            ),
            expected_stored_labels_cluster={
                'another_label': {
                    'plugin_name': 'labels',
                    'value': 'true',
                },
                'existing_label': {
                    'plugin_name': 'foo',
                    'value': 'bar',
                },
            },
            expected_stored_labels_node1={
                'node1_existing_label': {
                    'plugin_name': 'node1_plugin',
                    'value': 'true',
                },
            },
            expected_stored_labels_node2={},
        ),
    ),
]


@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.parametrize("discovery_test_case", _discovery_test_cases)
def test__discover_host_labels_and_services_on_realhost(realhost_scenario, discovery_test_case):
    scenario = realhost_scenario

    discovery_parameters = discovery_test_case.parameters

    with cmk_debug_enabled():
        discovered_services, host_label_discovery_result = discovery._discover_host_labels_and_services(
            scenario.hostname,
            scenario.ipaddress,
            scenario.multi_host_sections,
            discovery_parameters,
            check_plugin_whitelist={CheckPluginName('df')},
        )

    assert host_label_discovery_result.labels == DiscoveredHostLabels(
        HostLabel('cmk/check_mk_server', 'yes', plugin_name='labels'))

    services = {(s.check_plugin_name, s.item) for s in discovered_services}
    expected_services: Set = {
        (CheckPluginName('df'), '/boot/efi'),
    }

    assert services == expected_services


@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.parametrize("discovery_test_case", _discovery_test_cases)
def test__perform_host_label_discovery_on_realhost(realhost_scenario, discovery_test_case):
    scenario = realhost_scenario

    discovery_parameters = discovery_test_case.parameters

    with cmk_debug_enabled():
        _discovered_services, host_label_discovery_result = discovery._discover_host_labels_and_services(
            scenario.hostname,
            scenario.ipaddress,
            scenario.multi_host_sections,
            discovery_parameters,
            check_plugin_whitelist={CheckPluginName('df')},
        )

        return_host_labels, new_host_labels_per_plugin = discovery._perform_host_label_discovery(
            scenario.hostname,
            host_label_discovery_result.labels,
            discovery_parameters,
        )

    assert new_host_labels_per_plugin == Counter({"labels": 1})

    assert return_host_labels == discovery_test_case.on_realhost.expected_return_labels

    assert DiscoveredHostLabelsStore(
        scenario.hostname).load() == discovery_test_case.on_realhost.expected_stored_labels


@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.parametrize("discovery_test_case", _discovery_test_cases)
def test__discover_host_labels_and_services_on_cluster(cluster_scenario, discovery_test_case):
    scenario = cluster_scenario

    discovery_parameters = discovery_test_case.parameters

    with cmk_debug_enabled():
        discovered_services, host_label_discovery_result = discovery._get_cluster_services(
            scenario.host_config,
            scenario.ipaddress,
            scenario.multi_host_sections,
            discovery_parameters,
        )

    assert host_label_discovery_result.labels == DiscoveredHostLabels(
        HostLabel('cmk/check_mk_server', 'yes', plugin_name='labels'),
        HostLabel('node2_live_label', 'true', plugin_name='labels'),
    )

    services = set(discovered_services)
    expected_services: Set = {
        (CheckPluginName('df'), '/boot/efi'),
    }

    assert services == expected_services


@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.parametrize("discovery_test_case", _discovery_test_cases)
def test__perform_host_label_discovery_on_cluster(cluster_scenario, discovery_test_case):
    scenario = cluster_scenario

    discovery_parameters = discovery_test_case.parameters

    with cmk_debug_enabled():
        _discovered_services, host_label_discovery_result = discovery._get_cluster_services(
            scenario.host_config,
            scenario.ipaddress,
            scenario.multi_host_sections,
            discovery_parameters,
        )

        return_host_labels, new_host_labels_per_plugin = discovery._perform_host_label_discovery(
            scenario.host_config.hostname,
            host_label_discovery_result.labels,
            discovery_parameters,
        )

    assert new_host_labels_per_plugin == Counter({"labels": 2})

    assert return_host_labels == discovery_test_case.on_cluster.expected_return_labels

    assert (DiscoveredHostLabelsStore(scenario.host_config.hostname).load() ==
            discovery_test_case.on_cluster.expected_stored_labels_cluster)

    assert (DiscoveredHostLabelsStore(scenario.node1_hostname).load() ==
            discovery_test_case.on_cluster.expected_stored_labels_node1)

    assert (DiscoveredHostLabelsStore(scenario.node2_hostname).load() ==
            discovery_test_case.on_cluster.expected_stored_labels_node2)
