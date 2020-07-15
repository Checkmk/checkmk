#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name,protected-access

import pytest  # type: ignore[import]

from cmk.utils.type_defs import CheckPluginName, SectionName, SourceType

from cmk.base.data_sources.host_sections import HostKey, MultiHostSections
from cmk.base.data_sources.agent import AgentHostSections
import cmk.base.discovery as discovery
from cmk.base.discovered_labels import ServiceLabel, DiscoveredServiceLabels
import cmk.base.config as config


def test_discovered_service_init():
    ser = discovery.Service("abc", u"Item", u"ABC Item", None)
    assert ser.check_plugin_name == "abc"
    assert ser.item == u"Item"
    assert ser.description == u"ABC Item"
    assert ser.parameters is None
    assert ser.service_labels.to_dict() == {}

    ser = discovery.Service("abc", u"Item", u"ABC Item", None,
                            DiscoveredServiceLabels(ServiceLabel(u"läbel", u"lübel")))
    assert ser.service_labels.to_dict() == {u"läbel": u"lübel"}

    with pytest.raises(AttributeError):
        ser.xyz = "abc"  # type: ignore[attr-defined] # pylint: disable=assigning-non-slot


def test_discovered_service_eq():
    ser1 = discovery.Service("abc", u"Item", u"ABC Item", None)
    ser2 = discovery.Service("abc", u"Item", u"ABC Item", None)
    ser3 = discovery.Service("xyz", u"Item", u"ABC Item", None)
    ser4 = discovery.Service("abc", u"Xtem", u"ABC Item", None)
    ser5 = discovery.Service("abc", u"Item", u"ABC Item", [])

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
    service = discovery.Service("check_plugin_name", "item", "Test Description", None)
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
    service = discovery.Service("check_plugin_name", "item", "Test Description", None)
    assert service_filters.new is not None
    assert service_filters.new("hostname", service) is result


@pytest.fixture
def service_table() -> discovery.ServicesTable:
    return {
        ("check_plugin_name", "New Item 1"): ("new",
                                              discovery.Service("check_plugin_name", "New Item 1",
                                                                "Test Description New Item 1", {})),
        ("check_plugin_name", "New Item 2"): ("new",
                                              discovery.Service("check_plugin_name", "New Item 2",
                                                                "Test Description New Item 2", {})),
        ("check_plugin_name", "Vanished Item 1"):
            ("vanished",
             discovery.Service("check_plugin_name", "Vanished Item 1",
                               "Test Description Vanished Item 1", {})),
        ("check_plugin_name", "Vanished Item 2"):
            ("vanished",
             discovery.Service("check_plugin_name", "Vanished Item 2",
                               "Test Description Vanished Item 2", {})),
    }


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
def test__get_new_services(monkeypatch, service_table, mode, parameters_rediscovery,
                           result_new_item_names, result_counts):
    def _get_service_description(_hostname, _check_plugin_name, item):
        return "Test Description %s" % item

    monkeypatch.setattr(config, "service_description", _get_service_description)

    counts = discovery._empty_counts()

    params = {"inventory_rediscovery": parameters_rediscovery}
    service_filters = discovery.get_service_filter_funcs(params)

    new_item_names = [
        entry.item for entry in discovery._get_new_services(
            "hostname",
            service_table,
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
def test__check_service_table(monkeypatch, service_table, parameters, result_need_rediscovery):
    def _get_service_description(_hostname, _check_plugin_name, item):
        return "Test Description %s" % item

    monkeypatch.setattr(config, "service_description", _get_service_description)

    status, infotexts, long_infotexts, perfdata, need_rediscovery = discovery._check_service_table(
        "hostname", service_table, parameters)

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
        # we just care about the keys here, content set to [] for simplicity
        # section names have been are chosen arbitrarily.
        # any HostSections type is fine.
        HostKey("test_node", "1.2.3.4", SourceType.HOST): AgentHostSections({
            SectionName("kernel"): [],  # host only
            SectionName("uptime"): [],  # host & mgmt
        }),
        HostKey("test_node", "1.2.3.4", SourceType.MANAGEMENT): AgentHostSections({
            SectionName("uptime"): [],  # host & mgmt
            SectionName("liebert_fans"): [],  # mgmt only
            SectionName("mgmt_snmp_info"): [],  # is already mgmt_ prefixed
        }),
    }

    assert discovery._find_candidates_by_source_type(mhs, SourceType.HOST) == {
        CheckPluginName("kernel"),
        CheckPluginName('kernel_performance'),
        CheckPluginName('kernel_util'),
        CheckPluginName("uptime"),
    }

    assert discovery._find_candidates_by_source_type(mhs, SourceType.MANAGEMENT) == {
        CheckPluginName("liebert_fans"),
        CheckPluginName("uptime"),
        CheckPluginName("mgmt_snmp_info"),
    }

    assert discovery._find_candidates(mhs) == {
        CheckPluginName("kernel"),
        CheckPluginName('kernel_performance'),
        CheckPluginName('kernel_util'),
        CheckPluginName("uptime"),
        CheckPluginName("mgmt_liebert_fans"),
        CheckPluginName("mgmt_uptime"),
        CheckPluginName("mgmt_snmp_info"),  # not mgmt_mgmt_...
    }
