#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import re

import pytest  # type: ignore[import]
from testlib import CheckManager
from testlib.base import Scenario

from cmk.utils.exceptions import MKGeneralException
from cmk.base import config
import cmk.base.check_table as check_table
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
            ('smart.temp', '/dev/sda'): Service(
                check_plugin_name="smart.temp",
                item=u"/dev/sda",
                parameters={'levels': (35, 40)},
                description=u'Temperature SMART /dev/sda',
            ),
        }),
        # Static checks overwrite the autocheck definitions
        ("autocheck-overwrite", {
            ('smart.temp', '/dev/sda'): Service(
                check_plugin_name="smart.temp",
                item=u"/dev/sda",
                parameters={'levels': (35, 40)},
                description=u'Temperature SMART /dev/sda',
            ),
            ('smart.temp', '/dev/sdb'): Service(
                check_plugin_name='smart.temp',
                item=u'/dev/sdb',
                parameters={'is_autocheck': True},
                description=u'Temperature SMART /dev/sdb',
            ),
        }),
        ("ignore-not-existing-checks", {}),
        ("ignore-disabled-rules", {
            ('smart.temp', 'ITEM2'): Service(
                check_plugin_name='smart.temp',
                item=u"ITEM2",
                parameters={'levels': (35, 40)},
                description=u'Temperature SMART ITEM2',
            ),
        }),
        ("static-check-overwrite", {
            ('smart.temp', '/dev/sda'): Service(
                check_plugin_name="smart.temp",
                item=u"/dev/sda",
                parameters={
                    'levels': (35, 40),
                    'rule': 1
                },
                description=u'Temperature SMART /dev/sda',
            )
        }),
        ("node1", {
            ('smart.temp', 'auto-not-clustered'): Service(
                check_plugin_name="smart.temp",
                item=u"auto-not-clustered",
                parameters={},
                description=u'Temperature SMART auto-not-clustered',
            ),
            ('smart.temp', 'static-node1'): Service(check_plugin_name="smart.temp",
                                                    item=u"static-node1",
                                                    parameters={'levels': (35, 40)},
                                                    description=u'Temperature SMART static-node1'),
        }),
        ("cluster1", {
            ('smart.temp', 'static-cluster'): Service(
                check_plugin_name="smart.temp",
                item=u"static-cluster",
                parameters={'levels': (35, 40)},
                description=u'Temperature SMART static-cluster',
            ),
            ('smart.temp', 'auto-clustered'): Service(
                check_plugin_name="smart.temp",
                item=u"auto-clustered",
                parameters={'levels': (35, 40)},
                description=u'Temperature SMART auto-clustered',
            ),
        }),
    ])
def test_get_check_table(monkeypatch, hostname, expected_result):
    autochecks = {
        "ping-host": [Service("smart.temp", "bla", u'Temperature SMART bla', {})],
        "autocheck-overwrite": [
            Service('smart.temp', '/dev/sda', u'Temperature SMART /dev/sda',
                    {"is_autocheck": True}),
            Service('smart.temp', '/dev/sdb', u'Temperature SMART /dev/sdb',
                    {"is_autocheck": True}),
        ],
        "ignore-not-existing-checks": [Service("bla.blub", "ITEM", u'Blub ITEM', {}),],
        "node1": [
            Service("smart.temp", "auto-clustered", u"Temperature SMART auto-clustered", {}),
            Service("smart.temp", "auto-not-clustered", u'Temperature SMART auto-not-clustered', {})
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
    ("mgmt-board-ipmi", [("mgmt_ipmi_sensors", "TEMP X")]),
    ("ipmi-host", [("ipmi_sensors", "TEMP Y")]),
])
def test_get_check_table_of_mgmt_boards(monkeypatch, hostname, expected_result):
    autochecks = {
        "mgmt-board-ipmi": [
            Service("mgmt_ipmi_sensors", "TEMP X", "Management Interface: IPMI Sensor TEMP X", {}),
        ],
        "ipmi-host": [Service("ipmi_sensors", "TEMP Y", "IPMI Sensor TEMP Y", {}),]
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
        ("df_host", [("df", "/snap/core/9066")]),
        # old format, without TimespecificParamList
        ("df_host_1", [("df", "/snap/core/9067")]),
        ("df_host_2", [("df", "/snap/core/9068")]),
    ])
def test_get_check_table_of_static_check(monkeypatch, hostname, expected_result):
    static_checks = {
        "df_host": [
            Service('df', '/snap/core/9066', u'Filesystem /snap/core/9066', [{
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
                'df', '/snap/core/9067', u'Filesystem /snap/core/9067', {
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
        "df_host_2": [Service('df', '/snap/core/9068', u'Filesystem /snap/core/9068', None)],
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
            check_plugin_name="plugin %s" % d,
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
    sorted_service_list = check_table._get_sorted_service_list("", True, None, True)
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
    sorted_service_list = check_table._get_sorted_service_list("", True, None, True)
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
                           " 'description A' (plugin A / item), 'description B' (plugin B / item),"
                           " 'description D' (plugin D / item)")):
        _ = check_table._get_sorted_service_list("MyHost", True, None, True)
