#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name,protected-access
from typing import Dict, Sequence, Set, NamedTuple, Tuple

import pytest  # type: ignore[import]

# No stub files
from testlib.base import Scenario  # type: ignore[import]
from testlib.debug_utils import cmk_debug_enabled  # type: ignore[import]

from cmk.utils.type_defs import CheckPluginName, SectionName, SourceType, DiscoveryResult
from cmk.utils.labels import DiscoveredHostLabelsStore

from cmk.core_helpers.type_defs import NO_SELECTION

import cmk.base.ip_lookup as ip_lookup
from cmk.base.sources.agent import AgentHostSections
from cmk.base.sources.snmp import SNMPHostSections
from cmk.base.sources.host_sections import HostKey, ParsedSectionsBroker
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
            [],
        ),
        (CheckPluginName("check_plugin_name"), "New Item 2"): (
            "new",
            discovery.Service(
                CheckPluginName("check_plugin_name"),
                "New Item 2",
                "Test Description New Item 2",
                {},
            ),
            [],
        ),
        (CheckPluginName("check_plugin_name"), "Vanished Item 1"): (
            "vanished",
            discovery.Service(
                CheckPluginName("check_plugin_name"),
                "Vanished Item 1",
                "Test Description Vanished Item 1",
                {},
            ),
            [],
        ),
        (CheckPluginName("check_plugin_name"), "Vanished Item 2"): (
            "vanished",
            discovery.Service(
                CheckPluginName("check_plugin_name"),
                "Vanished Item 2",
                "Test Description Vanished Item 2",
                {},
            ),
            [],
        ),
    }


@pytest.fixture
def grouped_services() -> discovery.ServicesByTransition:
    return {
        "new": [
            autochecks.ServiceWithNodes(
                discovery.Service(
                    CheckPluginName("check_plugin_name"),
                    "New Item 1",
                    "Test Description New Item 1",
                    {},
                ),
                [],
            ),
            autochecks.ServiceWithNodes(
                discovery.Service(
                    CheckPluginName("check_plugin_name"),
                    "New Item 2",
                    "Test Description New Item 2",
                    {},
                ),
                [],
            ),
        ],
        "vanished": [
            autochecks.ServiceWithNodes(
                discovery.Service(
                    CheckPluginName("check_plugin_name"),
                    "Vanished Item 1",
                    "Test Description Vanished Item 1",
                    {},
                ),
                [],
            ),
            autochecks.ServiceWithNodes(
                discovery.Service(
                    CheckPluginName("check_plugin_name"),
                    "Vanished Item 2",
                    "Test Description Vanished Item 2",
                    {},
                ),
                [],
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

    result = DiscoveryResult()

    params = {"inventory_rediscovery": parameters_rediscovery}
    service_filters = discovery.get_service_filter_funcs(params)

    new_item_names = [
        entry.service.item or "" for entry in discovery._get_post_discovery_services(
            "hostname",
            grouped_services,
            service_filters,
            result,
            mode,
        )
    ]

    count_new, count_kept, count_removed = result_counts

    assert sorted(new_item_names) == sorted(result_new_item_names)
    assert result.self_new == count_new
    assert result.self_kept == count_kept
    assert result.self_removed == count_removed


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


@pytest.mark.usefixtures("load_all_agent_based_plugins")
def test__find_candidates():
    broker = ParsedSectionsBroker()

    broker._data = {
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

    assert discovery._discovered_services._find_host_candidates(
        broker,
        preliminary_candidates,
        parsed_sections_of_interest,
    ) == {
        CheckPluginName('docker_container_status_uptime'),
        CheckPluginName("kernel"),
        CheckPluginName('kernel_performance'),
        CheckPluginName('kernel_util'),
        CheckPluginName("uptime"),
    }

    assert discovery._discovered_services._find_mgmt_candidates(
        broker,
        preliminary_candidates,
        parsed_sections_of_interest,
    ) == {
        CheckPluginName('mgmt_docker_container_status_uptime'),
        CheckPluginName("mgmt_liebert_fans"),
        CheckPluginName("mgmt_uptime"),
    }

    assert discovery._discovered_services._find_candidates(
        broker,
        run_only_plugin_names=None,
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


@pytest.mark.usefixtures("load_all_agent_based_plugins")
def test_do_discovery(monkeypatch):
    ts = Scenario().add_host("test-host", ipaddress="127.0.0.1")
    ts.fake_standard_linux_agent_output("test-host")
    ts.apply(monkeypatch)

    with cmk_debug_enabled():
        discovery.do_discovery(
            arg_hostnames={"test-host"},
            selected_sections=NO_SELECTION,
            run_only_plugin_names=None,
            arg_only_new=False,
        )

    services = autochecks.parse_autochecks_file("test-host", config.service_description)
    found = {(s.check_plugin_name, s.item): s.service_labels.to_dict() for s in services}
    assert found == _expected_services

    store = DiscoveredHostLabelsStore("test-host")
    assert store.load() == _expected_host_labels


RealHostScenario = NamedTuple("RealHostScenario", [
    ("hostname", str),
    ("ipaddress", str),
    ("parsed_sections_broker", ParsedSectionsBroker),
])


@pytest.fixture(name="realhost_scenario")
def _realhost_scenario(monkeypatch):
    hostname = "test-realhost"
    ipaddress = "1.2.3.4"
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

    def fake_lookup_ip_address(host_config, *, family, for_mgmt_board=True):
        return ipaddress

    monkeypatch.setattr(ip_lookup, "lookup_ip_address", fake_lookup_ip_address)

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

    broker = ParsedSectionsBroker()
    broker.update({
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
                            '/boot/test-efi',
                        ],
                        [
                            'tmpfs',
                            'tmpfs',
                            '8152916',
                            '244',
                            '8152672',
                            '1%',
                            '/opt/omd/sites/test-heute/tmp',
                        ],
                    ],
                })
    })

    return RealHostScenario(hostname, ipaddress, broker)


ClusterScenario = NamedTuple("ClusterScenario", [
    ("host_config", config.HostConfig),
    ("ipaddress", str),
    ("parsed_sections_broker", ParsedSectionsBroker),
    ("node1_hostname", str),
    ("node2_hostname", str),
])


@pytest.fixture(name="cluster_scenario")
def _cluster_scenario(monkeypatch):
    hostname = "test-clusterhost"
    ipaddress = "1.2.3.4"
    node1_hostname = 'test-node1'
    node2_hostname = 'test-node2'

    def fake_lookup_ip_address(host_config, *, family, for_mgmt_board=True):
        return ipaddress

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
    host_config = ts.apply(monkeypatch).get_host_config(hostname)

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

    broker = ParsedSectionsBroker()
    broker.update({
        HostKey(hostname=node1_hostname, ipaddress=ipaddress, source_type=SourceType.HOST):
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
                            '/boot/test-efi',
                        ],
                        [
                            'tmpfs',
                            'tmpfs',
                            '8152916',
                            '244',
                            '8152672',
                            '1%',
                            '/opt/omd/sites/test-heute/tmp',
                        ],
                    ],
                }),
        HostKey(hostname=node2_hostname, ipaddress=ipaddress, source_type=SourceType.HOST):
            AgentHostSections(
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
                            '/boot/test-efi',
                        ],
                        [
                            'tmpfs',
                            'tmpfs',
                            '8152916',
                            '244',
                            '8152672',
                            '1%',
                            '/opt/omd/sites/test-heute2/tmp',
                        ],
                    ],
                }),
    })

    return ClusterScenario(
        host_config,
        ipaddress,
        broker,
        node1_hostname,
        node2_hostname,
    )


ExpectedDiscoveryResultRealHost = NamedTuple("ExpectedDiscoveryResultRealHost", [
    ("expected_vanished_host_labels", Sequence[HostLabel]),
    ("expected_old_host_labels", Sequence[HostLabel]),
    ("expected_new_host_labels", Sequence[HostLabel]),
    ("expected_stored_labels", Dict),
])

ExpectedDiscoveryResultCluster = NamedTuple("ExpectedDiscoveryResultCluster", [
    ("expected_vanished_host_labels", Sequence[HostLabel]),
    ("expected_old_host_labels", Sequence[HostLabel]),
    ("expected_new_host_labels", Sequence[HostLabel]),
    ("expected_stored_labels_cluster", Dict),
    ("expected_stored_labels_node1", Dict),
    ("expected_stored_labels_node2", Dict),
])

DiscoveryTestCase = NamedTuple("DiscoveryTestCase", [
    ("parameters", discovery.DiscoveryParameters),
    ("expected_services", Set[Tuple[CheckPluginName, str]]),
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
            only_host_labels=False,
        ),
        expected_services={
            (CheckPluginName('df'), '/boot/test-efi'),
            (CheckPluginName('df'), '/opt/omd/sites/test-heute/tmp'),
        },
        on_realhost=ExpectedDiscoveryResultRealHost(
            expected_vanished_host_labels=[
                HostLabel('existing_label', 'bar', SectionName('foo')),
                HostLabel('another_label', 'true', SectionName('labels')),
            ],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel('cmk/check_mk_server', 'yes', SectionName('labels')),
            ],
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
            expected_vanished_host_labels=[
                HostLabel('existing_label', 'bar', SectionName('foo')),
                HostLabel('another_label', 'true', SectionName('labels')),
            ],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel('node1_existing_label', 'true', SectionName('node1_plugin')),
                HostLabel('cmk/check_mk_server', 'yes', SectionName('labels')),
                HostLabel('node2_live_label', 'true', SectionName('labels')),
            ],
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
                'node1_existing_label': {
                    'plugin_name': 'node1_plugin',
                    'value': 'true',
                },
                'node2_live_label': {
                    'plugin_name': 'labels',
                    'value': 'true',
                },
            },
            expected_stored_labels_node1={
                'cmk/check_mk_server': {
                    'plugin_name': 'labels',
                    'value': 'yes',
                },
                'node1_existing_label': {
                    'plugin_name': 'node1_plugin',
                    'value': 'true',
                },
            },
            expected_stored_labels_node2={
                'node2_live_label': {
                    'plugin_name': 'labels',
                    'value': 'true',
                },
            },
        ),
    ),
    # check discovery
    DiscoveryTestCase(
        parameters=discovery.DiscoveryParameters(
            on_error="raise",
            load_labels=True,
            save_labels=False,
            only_host_labels=False,
        ),
        expected_services={
            (CheckPluginName('df'), '/boot/test-efi'),
        },
        on_realhost=ExpectedDiscoveryResultRealHost(
            expected_vanished_host_labels=[
                HostLabel('existing_label', 'bar', SectionName('foo')),
                HostLabel('another_label', 'true', SectionName('labels')),
            ],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel('cmk/check_mk_server', 'yes', SectionName('labels')),
            ],
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
            expected_vanished_host_labels=[
                HostLabel('existing_label', 'bar', SectionName('foo')),
                HostLabel('another_label', 'true', SectionName('labels')),
            ],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel('node1_existing_label', 'true', SectionName('node1_plugin')),
                HostLabel('cmk/check_mk_server', 'yes', SectionName('labels')),
                HostLabel('node2_live_label', 'true', SectionName('labels')),
            ],
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
            only_host_labels=False,
        ),
        expected_services={
            (CheckPluginName('df'), '/boot/test-efi'),
            (CheckPluginName('df'), '/opt/omd/sites/test-heute/tmp'),
        },
        on_realhost=ExpectedDiscoveryResultRealHost(
            expected_vanished_host_labels=[],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel('cmk/check_mk_server', 'yes', SectionName('labels')),
            ],
            expected_stored_labels={
                'cmk/check_mk_server': {
                    'plugin_name': 'labels',
                    'value': 'yes',
                },
            },
        ),
        on_cluster=ExpectedDiscoveryResultCluster(
            expected_vanished_host_labels=[],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel('cmk/check_mk_server', 'yes', SectionName('labels')),
                HostLabel('node2_live_label', 'true', SectionName('labels')),
            ],
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
                'cmk/check_mk_server': {
                    'plugin_name': 'labels',
                    'value': 'yes',
                },
            },
            expected_stored_labels_node2={
                'node2_live_label': {
                    'plugin_name': 'labels',
                    'value': 'true',
                },
            },
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
            only_host_labels=False,
        ),
        expected_services={
            (CheckPluginName('df'), '/boot/test-efi'),
        },
        on_realhost=ExpectedDiscoveryResultRealHost(
            expected_vanished_host_labels=[],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel('cmk/check_mk_server', 'yes', SectionName('labels')),
            ],
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
            expected_vanished_host_labels=[],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel('cmk/check_mk_server', 'yes', SectionName('labels')),
                HostLabel('node2_live_label', 'true', SectionName('labels')),
            ],
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
    # discover on host: mode == "only-host-labels"
    # Only discover host labels
    DiscoveryTestCase(
        parameters=discovery.DiscoveryParameters(
            on_error="raise",
            load_labels=False,
            save_labels=False,
            only_host_labels=True,
        ),
        expected_services=set(),
        on_realhost=ExpectedDiscoveryResultRealHost(
            expected_vanished_host_labels=[],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel('cmk/check_mk_server', 'yes', SectionName('labels')),
            ],
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
            expected_vanished_host_labels=[],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel('cmk/check_mk_server', 'yes', SectionName('labels')),
                HostLabel('node2_live_label', 'true', SectionName('labels')),
            ],
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


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize("discovery_test_case", _discovery_test_cases)
def test__discover_host_labels_and_services_on_realhost(realhost_scenario, discovery_test_case):
    scenario = realhost_scenario

    discovery_parameters = discovery_test_case.parameters

    # we're depending on the changed host labels:
    _ = discovery.analyse_host_labels(
        host_name=scenario.hostname,
        ipaddress=scenario.ipaddress,
        parsed_sections_broker=scenario.parsed_sections_broker,
        discovery_parameters=discovery_parameters,
    )

    with cmk_debug_enabled():
        discovered_services = ([] if discovery_parameters.only_host_labels else
                               discovery._discovered_services._discover_services(
                                   host_name=scenario.hostname,
                                   ipaddress=scenario.ipaddress,
                                   parsed_sections_broker=scenario.parsed_sections_broker,
                                   discovery_parameters=discovery_parameters,
                                   run_only_plugin_names=None,
                               ))

    services = {(s.check_plugin_name, s.item) for s in discovered_services}

    assert services == discovery_test_case.expected_services


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize("discovery_test_case", _discovery_test_cases)
def test__perform_host_label_discovery_on_realhost(realhost_scenario, discovery_test_case):
    scenario = realhost_scenario

    discovery_parameters = discovery_test_case.parameters

    with cmk_debug_enabled():
        host_label_result = discovery.analyse_host_labels(
            host_name=scenario.hostname,
            ipaddress=scenario.ipaddress,
            parsed_sections_broker=scenario.parsed_sections_broker,
            discovery_parameters=discovery_parameters,
        )

    assert host_label_result.vanished == discovery_test_case.on_realhost.expected_vanished_host_labels
    assert host_label_result.old == discovery_test_case.on_realhost.expected_old_host_labels
    assert host_label_result.new == discovery_test_case.on_realhost.expected_new_host_labels

    assert DiscoveredHostLabelsStore(
        scenario.hostname).load() == discovery_test_case.on_realhost.expected_stored_labels


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize("discovery_test_case", _discovery_test_cases)
def test__discover_host_labels_and_services_on_cluster(cluster_scenario, discovery_test_case):
    scenario = cluster_scenario

    discovery_parameters = discovery_test_case.parameters

    # we need the sideeffects of this call. TODO: guess what.
    _ = discovery._host_labels.analyse_cluster_host_labels(
        host_config=scenario.host_config,
        ipaddress=scenario.ipaddress,
        parsed_sections_broker=scenario.parsed_sections_broker,
        discovery_parameters=discovery_parameters,
    )

    with cmk_debug_enabled():
        discovered_services = discovery._get_cluster_services(
            scenario.host_config,
            scenario.ipaddress,
            scenario.parsed_sections_broker,
            discovery_parameters,
        )

    services = set(discovered_services)

    assert services == discovery_test_case.expected_services


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize("discovery_test_case", _discovery_test_cases)
def test__perform_host_label_discovery_on_cluster(cluster_scenario, discovery_test_case):
    scenario = cluster_scenario

    discovery_parameters = discovery_test_case.parameters

    with cmk_debug_enabled():
        host_label_result = discovery._host_labels.analyse_cluster_host_labels(
            host_config=scenario.host_config,
            ipaddress=scenario.ipaddress,
            parsed_sections_broker=scenario.parsed_sections_broker,
            discovery_parameters=discovery_parameters,
        )

    assert (
        host_label_result.vanished == discovery_test_case.on_cluster.expected_vanished_host_labels)
    assert host_label_result.old == discovery_test_case.on_cluster.expected_old_host_labels
    assert host_label_result.new == discovery_test_case.on_cluster.expected_new_host_labels

    assert DiscoveredHostLabelsStore(scenario.host_config.hostname).load(
    ) == discovery_test_case.on_cluster.expected_stored_labels_cluster

    assert (DiscoveredHostLabelsStore(scenario.node1_hostname).load() ==
            discovery_test_case.on_cluster.expected_stored_labels_node1)

    assert (DiscoveredHostLabelsStore(scenario.node2_hostname).load() ==
            discovery_test_case.on_cluster.expected_stored_labels_node2)
