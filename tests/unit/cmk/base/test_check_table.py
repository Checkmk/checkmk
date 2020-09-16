#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import re

from typing import Dict, List

import pytest  # type: ignore[import]
# No stub file
from testlib import CheckManager  # type: ignore[import]
# No stub file
from testlib.base import Scenario  # type: ignore[import]

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import CheckPluginName

import cmk.base.api.agent_based.register as agent_based_register

from cmk.base import config
from cmk.base import check_table
from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.check_utils import Service


# TODO: This misses a lot of cases
# - different get_check_table arguments
@pytest.mark.parametrize(
    "hostname,expected_result",
    [
        ("empty-host", {}),
        # Skip the autochecks automatically for ping hosts
        ("ping-host", {}),
        ("no-autochecks", {
            (CheckPluginName('smart_temp'), '/dev/sda'): Service(
                check_plugin_name=CheckPluginName("smart_temp"),
                item=u"/dev/sda",
                parameters={'levels': (35, 40)},
                description=u'Temperature SMART /dev/sda',
            ),
        }),
        # Static checks overwrite the autocheck definitions
        ("autocheck-overwrite", {
            (CheckPluginName('smart_temp'), '/dev/sda'): Service(
                check_plugin_name=CheckPluginName("smart_temp"),
                item=u"/dev/sda",
                parameters={'levels': (35, 40)},
                description=u'Temperature SMART /dev/sda',
            ),
            (CheckPluginName('smart_temp'), '/dev/sdb'): Service(
                check_plugin_name=CheckPluginName('smart_temp'),
                item=u'/dev/sdb',
                parameters={'is_autocheck': True},
                description=u'Temperature SMART /dev/sdb',
            ),
        }),
        ("ignore-not-existing-checks", {}),
        ("ignore-disabled-rules", {
            (CheckPluginName('smart_temp'), 'ITEM2'): Service(
                check_plugin_name=CheckPluginName('smart_temp'),
                item=u"ITEM2",
                parameters={'levels': (35, 40)},
                description=u'Temperature SMART ITEM2',
            ),
        }),
        ("static-check-overwrite", {
            (CheckPluginName('smart_temp'), '/dev/sda'): Service(
                check_plugin_name=CheckPluginName("smart_temp"),
                item=u"/dev/sda",
                parameters={
                    'levels': (35, 40),
                    'rule': 1
                },
                description=u'Temperature SMART /dev/sda',
            )
        }),
        ("node1", {
            (CheckPluginName('smart_temp'), 'auto-not-clustered'): Service(
                check_plugin_name=CheckPluginName("smart_temp"),
                item=u"auto-not-clustered",
                parameters={},
                description=u'Temperature SMART auto-not-clustered',
            ),
            (CheckPluginName('smart_temp'), 'static-node1'): Service(
                check_plugin_name=CheckPluginName("smart_temp"),
                item=u"static-node1",
                parameters={'levels': (35, 40)},
                description=u'Temperature SMART static-node1'),
        }),
        ("cluster1", {
            (CheckPluginName('smart_temp'), 'static-cluster'): Service(
                check_plugin_name=CheckPluginName("smart_temp"),
                item=u"static-cluster",
                parameters={'levels': (35, 40)},
                description=u'Temperature SMART static-cluster',
            ),
            (CheckPluginName('smart_temp'), 'auto-clustered'): Service(
                check_plugin_name=CheckPluginName("smart_temp"),
                item=u"auto-clustered",
                parameters={'levels': (35, 40)},
                description=u'Temperature SMART auto-clustered',
            ),
        }),
    ])
def test_get_check_table(monkeypatch, hostname, expected_result):
    autochecks = {
        "ping-host": [Service(
            CheckPluginName("smart_temp"),
            "bla",
            u'Temperature SMART bla',
            {},
        )],
        "autocheck-overwrite": [
            Service(
                CheckPluginName('smart_temp'),
                '/dev/sda',
                u'Temperature SMART /dev/sda',
                {"is_autocheck": True},
            ),
            Service(
                CheckPluginName('smart_temp'),
                '/dev/sdb',
                u'Temperature SMART /dev/sdb',
                {"is_autocheck": True},
            ),
        ],
        "ignore-not-existing-checks": [
            Service(
                CheckPluginName("bla_blub"),
                "ITEM",
                u'Blub ITEM',
                {},
            ),
        ],
        "node1": [
            Service(
                CheckPluginName("smart_temp"),
                "auto-clustered",
                u"Temperature SMART auto-clustered",
                {},
            ),
            Service(
                CheckPluginName("smart_temp"),
                "auto-not-clustered",
                u'Temperature SMART auto-not-clustered',
                {},
            )
        ],
    }

    ts = Scenario().add_host(hostname, tags={"criticality": "test"})
    ts.add_host("ping-host", tags={"agent": "no-agent"})
    ts.add_host("node1")
    ts.add_cluster("cluster1", nodes=["node1"])
    ts.set_option(
        "static_checks",
        {
            "temperature": [
                (('smart.temp', '/dev/sda', {}), [], ["no-autochecks", "autocheck-overwrite"]),
                (('blub.bla', 'ITEM', {}), [], ["ignore-not-existing-checks"]),
                (('smart.temp', 'ITEM1', {}), [], ["ignore-disabled-rules"], {
                    "disabled": True
                }),
                (('smart.temp', 'ITEM2', {}), [], ["ignore-disabled-rules"]),
                (('smart.temp', '/dev/sda', {
                    "rule": 1
                }), [], ["static-check-overwrite"]),
                (('smart.temp', '/dev/sda', {
                    "rule": 2
                }), [], ["static-check-overwrite"]),
                (('smart.temp', 'static-node1', {}), [], ["node1"]),
                (('smart.temp', 'static-cluster', {}), [], ["cluster1"]),
            ]
        },
    )
    ts.set_ruleset("clustered_services", [
        ([], ['node1'], [u'Temperature SMART auto-clustered$']),
    ])
    config_cache = ts.apply(monkeypatch)
    monkeypatch.setattr(config_cache, "get_autochecks_of", lambda h: autochecks.get(h, []))

    CheckManager().load(["smart"])
    assert check_table.get_check_table(hostname) == expected_result


@pytest.mark.parametrize("hostname, expected_result", [
    ("mgmt-board-ipmi", [(CheckPluginName("mgmt_ipmi_sensors"), "TEMP X")]),
    ("ipmi-host", [(CheckPluginName("ipmi_sensors"), "TEMP Y")]),
])
def test_get_check_table_of_mgmt_boards(monkeypatch, hostname, expected_result):
    autochecks = {
        "mgmt-board-ipmi": [
            Service(CheckPluginName("mgmt_ipmi_sensors"), "TEMP X",
                    "Management Interface: IPMI Sensor TEMP X", {}),
        ],
        "ipmi-host": [
            Service(CheckPluginName("ipmi_sensors"), "TEMP Y", "IPMI Sensor TEMP Y", {}),
        ]
    }

    ts = Scenario().add_host("mgmt-board-ipmi",
                             tags={
                                 'piggyback': 'auto-piggyback',
                                 'networking': 'lan',
                                 'address_family': 'no-ip',
                                 'criticality': 'prod',
                                 'snmp_ds': 'no-snmp',
                                 'site': 'heute',
                                 'agent': 'no-agent'
                             })
    ts.add_host("ipmi-host",
                tags={
                    'piggyback': 'auto-piggyback',
                    'networking': 'lan',
                    'agent': 'cmk-agent',
                    'criticality': 'prod',
                    'snmp_ds': 'no-snmp',
                    'site': 'heute',
                    'address_family': 'ip-v4-only'
                })
    ts.set_option("management_protocol", {"mgmt-board-ipmi": "ipmi"})

    config_cache = ts.apply(monkeypatch)
    monkeypatch.setattr(config_cache, "get_autochecks_of", lambda h: autochecks.get(h, []))

    CheckManager().load(["mgmt_ipmi_sensors", "ipmi_sensors"])
    assert list(check_table.get_check_table(hostname).keys()) == expected_result


# verify static check outcome, including timespecific params
@pytest.mark.parametrize(
    "hostname,expected_result",
    [
        ("df_host", [(CheckPluginName("df"), "/snap/core/9066")]),
        # old format, without TimespecificParamList
        ("df_host_1", [(CheckPluginName("df"), "/snap/core/9067")]),
        ("df_host_2", [(CheckPluginName("df"), "/snap/core/9068")]),
    ])
def test_get_check_table_of_static_check(monkeypatch, hostname, expected_result):
    static_checks = {
        "df_host": [
            Service(CheckPluginName('df'), '/snap/core/9066', u'Filesystem /snap/core/9066', [{
                'tp_values': [('24X7', {
                    'inodes_levels': None
                })],
                'tp_default_value': {}
            }, {
                'trend_range': 24,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'magic_normsize': 20,
                'show_inodes': 'onlow',
                'levels': (80.0, 90.0),
                'show_reserved': False,
                'levels_low': (50.0, 60.0),
                'trend_perfdata': True
            }]),
        ],
        "df_host_1": [
            Service(
                CheckPluginName('df'), '/snap/core/9067', u'Filesystem /snap/core/9067', {
                    'trend_range': 24,
                    'show_levels': 'onmagic',
                    'inodes_levels': (10.0, 5.0),
                    'magic_normsize': 20,
                    'show_inodes': 'onlow',
                    'levels': (80.0, 90.0),
                    'tp_default_value': {
                        'levels': (87.0, 90.0)
                    },
                    'show_reserved': False,
                    'tp_values': [('24X7', {
                        'inodes_levels': None
                    })],
                    'levels_low': (50.0, 60.0),
                    'trend_perfdata': True
                })
        ],
        "df_host_2": [
            Service(CheckPluginName('df'), '/snap/core/9068', u'Filesystem /snap/core/9068', None)
        ],
    }

    ts = Scenario().add_host(hostname, tags={"criticality": "test"})
    ts.add_host("df_host")
    ts.add_host("df_host_1")
    ts.add_host("df_host_2")
    ts.set_option(
        "static_checks",
        {
            "filesystem": [
                (('df', '/snap/core/9066', [{
                    'tp_values': [('24X7', {
                        'inodes_levels': None
                    })],
                    'tp_default_value': {}
                }, {
                    'trend_range': 24,
                    'show_levels': 'onmagic',
                    'inodes_levels': (10.0, 5.0),
                    'magic_normsize': 20,
                    'show_inodes': 'onlow',
                    'levels': (80.0, 90.0),
                    'show_reserved': False,
                    'levels_low': (50.0, 60.0),
                    'trend_perfdata': True
                }]), [], ["df_host"]),
                (('df', '/snap/core/9067', [{
                    'tp_values': [('24X7', {
                        'inodes_levels': None
                    })],
                    'tp_default_value': {}
                }, {
                    'trend_range': 24,
                    'show_levels': 'onmagic',
                    'inodes_levels': (10.0, 5.0),
                    'magic_normsize': 20,
                    'show_inodes': 'onlow',
                    'levels': (80.0, 90.0),
                    'show_reserved': False,
                    'levels_low': (50.0, 60.0),
                    'trend_perfdata': True
                }]), [], ["df_host_1"]),
                (('df', '/snap/core/9068', None), [], ["df_host_2"]),
            ],
        },
    )

    config_cache = ts.apply(monkeypatch)
    monkeypatch.setattr(config_cache, "get_autochecks_of", lambda h: static_checks.get(h, []))

    CheckManager().load(["df"])
    assert list(check_table.get_check_table(hostname).keys()) == expected_result


@pytest.fixture(name="service_list")
def _service_list():
    return [
        Service(
            check_plugin_name=CheckPluginName("plugin_%s" % d),
            item="item",
            description="description %s" % d,
            parameters={},
        ) for d in "FDACEB"
    ]


def test_get_sorted_check_table_cmc(monkeypatch, service_list):
    monkeypatch.setattr(config, "is_cmc", lambda: True)
    monkeypatch.setattr(check_table, "get_check_table",
                        lambda *a, **kw: {s.id(): s for s in service_list})

    # all arguments are ignored in test
    sorted_service_list = check_table.get_sorted_service_list(
        "",
        filter_mode=None,
        skip_ignored=True,
    )
    assert sorted_service_list == sorted(service_list, key=lambda s: s.description)


def test_get_sorted_check_table_no_cmc(monkeypatch, service_list):
    monkeypatch.setattr(config, "is_cmc", lambda: False)
    monkeypatch.setattr(check_table, "get_check_table",
                        lambda *a, **kw: {s.id(): s for s in service_list})
    monkeypatch.setattr(
        config, "service_depends_on", lambda _hn, descr: {
            "description A": ["description C"],
            "description B": ["description D"],
            "description D": ["description A", "description F"],
        }.get(descr, []))

    # all arguments are ignored in test
    sorted_service_list = check_table.get_sorted_service_list(
        "",
        filter_mode=None,
        skip_ignored=True,
    )
    assert [s.description for s in sorted_service_list] == [
        "description C",  #
        "description E",  # no deps, alphabetical order
        "description F",  #
        "description A",
        "description D",
        "description B",
    ]


def test_get_sorted_check_table_cyclic(monkeypatch, service_list):
    monkeypatch.setattr(config, "is_cmc", lambda: False)
    monkeypatch.setattr(check_table, "get_check_table",
                        lambda *a, **kw: {s.id(): s for s in service_list})
    monkeypatch.setattr(
        config, "service_depends_on", lambda _hn, descr: {
            "description A": ["description B"],
            "description B": ["description D"],
            "description D": ["description A"],
        }.get(descr, []))

    with pytest.raises(MKGeneralException,
                       match=re.escape(
                           "Cyclic service dependency of host MyHost. Problematic are:"
                           " 'description A' (plugin_A / item), 'description B' (plugin_B / item),"
                           " 'description D' (plugin_D / item)")):
        _ = check_table.get_sorted_service_list(
            "MyHost",
            filter_mode=None,
            skip_ignored=True,
        )


@pytest.mark.parametrize("check_group_parameters", [
    {},
    {
        'levels': (4, 5, 6, 7),
    },
])
def test_check_table__get_static_check_entries(monkeypatch, check_group_parameters):
    hostname = "hostname"
    static_parameters = {
        'levels': (1, 2, 3, 4),
    }
    static_checks: Dict[str, List] = {
        "ps": [(('ps', 'item', static_parameters), [], [hostname], {})],
    }

    ts = Scenario().add_host(hostname)
    ts.set_option("static_checks", static_checks)

    ts.set_ruleset("checkgroup_parameters", {
        'ps': [(check_group_parameters, [hostname], [], {})],
    })

    config_cache = ts.apply(monkeypatch)

    monkeypatch.setattr(
        agent_based_register,
        "get_check_plugin",
        lambda cpn: CheckPlugin(
            CheckPluginName("ps"),
            [],
            "Process item",
            None,  # type: ignore
            None,  # type: ignore
            None,  # type: ignore
            None,  # type: ignore
            None,  # type: ignore
            {},
            "ps",  # type: ignore
            None,  # type: ignore
            None,  # type: ignore
        ))

    host_config = config_cache.get_host_config(hostname)
    static_check_parameters = [
        service.parameters
        for service in check_table.HostCheckTable._get_static_check_entries(host_config)
    ]

    entries = config._get_checkgroup_parameters(
        config_cache,
        hostname,
        "ps",
        "item",
        "Process item",
    )

    assert len(entries) == 1
    assert entries[0] == check_group_parameters

    assert len(static_check_parameters) == 1
    static_check_parameter = static_check_parameters[0]
    assert static_check_parameter == static_parameters
