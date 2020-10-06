#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
from pathlib import Path

import pytest  # type: ignore[import]

from testlib.base import Scenario

import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import CheckPluginName

import cmk.base.autochecks as autochecks
import cmk.base.config as config
import cmk.base.discovery as discovery
from cmk.base.check_utils import Service
from cmk.base.discovered_labels import (
    DiscoveredServiceLabels,
    ServiceLabel,
)


@pytest.fixture(autouse=True)
def autochecks_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(cmk.utils.paths, "autochecks_dir", str(tmp_path))


@pytest.fixture()
def test_config(monkeypatch):
    ts = Scenario().add_host("host")
    return ts.apply(monkeypatch)


@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.parametrize(
    "autochecks_content,expected_result",
    [
        (u"[]", []),
        (u"", []),
        (u"@", []),
        (u"[abc123]", []),
        # Dict: Allow non string items
        (
            u"""[
  {'check_plugin_name': 'df', 'item': u'123', 'parameters': {}, 'service_labels': {}},
]""",
            [
                Service(
                    CheckPluginName('df'), '123', u"", {
                        'inodes_levels': (10.0, 5.0),
                        'levels': (80.0, 90.0),
                        'levels_low': (50.0, 60.0),
                        'magic_normsize': 20,
                        'show_inodes': 'onlow',
                        'show_levels': 'onmagic',
                        'show_reserved': False,
                        'trend_perfdata': True,
                        'trend_range': 24
                    }),
            ],
        ),
        # Dict: Exception on invalid check type
        (
            u"""[
  {'check_plugin_name': 123, 'item': 'abc', 'parameters': {}, 'service_labels': {}},
]""",
            MKGeneralException,
        ),
        # Dict: Exception on name reference behaves like SyntaxError
        (
            u"""[
  {'check_plugin_name': 'cpu_loads', 'item': None, 'parameters': cpuload_default_levels, 'service_labels': {}},
]""",
            [],
        ),
        # Dict: Regular processing
        (
            u"""[
  {'check_plugin_name': 'df', 'item': u'/', 'parameters': {}, 'service_labels': {}},
  {'check_plugin_name': 'cpu_loads', 'item': None, 'parameters': {}, 'service_labels': {}},
  {'check_plugin_name': 'lnx_if', 'item': u'2', 'parameters': {'state': ['1'], 'speed': 10000000}, 'service_labels': {}},
]""",
            [
                Service(
                    CheckPluginName('df'), u'/', u"", {
                        'inodes_levels': (10.0, 5.0),
                        'levels': (80.0, 90.0),
                        'levels_low': (50.0, 60.0),
                        'magic_normsize': 20,
                        'show_inodes': 'onlow',
                        'show_levels': 'onmagic',
                        'show_reserved': False,
                        'trend_perfdata': True,
                        'trend_range': 24
                    }),
                Service(CheckPluginName('cpu_loads'), None, u"", (5.0, 10.0)),
                Service(CheckPluginName('lnx_if'), u'2', u"", {
                    'errors': (0.01, 0.1),
                    'speed': 10000000,
                    'state': ['1']
                }),
            ],
        ),
    ])
def test_manager_get_autochecks_of(test_config, autochecks_content, expected_result):
    autochecks_file = Path(cmk.utils.paths.autochecks_dir, "host.mk")
    with autochecks_file.open("w", encoding="utf-8") as f:
        f.write(autochecks_content)

    manager = test_config._autochecks_manager

    if expected_result is MKGeneralException:
        with pytest.raises(MKGeneralException):
            manager.get_autochecks_of("host", config.compute_check_parameters,
                                      config.service_description)
        return

    result = manager.get_autochecks_of("host", config.compute_check_parameters,
                                       config.service_description)
    assert result == expected_result

    # Check that the ConfigCache method also returns the correct data
    assert test_config.get_autochecks_of("host") == result

    # Check that there are no str items (None, int, ...)
    assert all(not isinstance(s.item, bytes) for s in result)
    # All desriptions need to be of type text
    assert all(isinstance(s.description, str) for s in result)


def test_parse_autochecks_file_not_existing():
    assert autochecks.parse_autochecks_file("host", config.service_description) == []


@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.parametrize(
    "autochecks_content,expected_result",
    [
        (u"[]", []),
        (u"", []),
        (u"@", MKGeneralException),
        (u"[abc123]", MKGeneralException),
        # Tuple: Handle old format
        (u"""[
  ('hostxyz', 'df', '/', {}),
]""", [
            (CheckPluginName('df'), u'/', {}),
        ]),
        # Tuple: Convert non unicode item
        (
            u"""[
          ('df', '/', {}),
        ]""",
            [
                (CheckPluginName('df'), u'/', {}),
            ],
        ),
        # Tuple: Regular processing
        (
            u"""[
          ('df', u'/', {}),
          ('df', u'/xyz', "lala"),
          ('df', u'/zzz', ['abc', 'xyz']),
          ('cpu.loads', None, cpuload_default_levels),
          ('chrony', None, {}),
          ('lnx_if', u'2', {'state': ['1'], 'speed': 10000000}),
          ('if64', u'00001001', { "errors" : if_default_error_levels, "traffic" : if_default_traffic_levels, "average" : if_default_average , "state" : "1", "speed" : 1000000000}),
        ]""",
            [
                (CheckPluginName('df'), u'/', {}),
                (CheckPluginName('df'), u'/xyz', 'lala'),
                (CheckPluginName('df'), u'/zzz', ['abc', 'xyz']),
                (CheckPluginName('cpu_loads'), None, (5.0, 10.0)),
                (CheckPluginName('chrony'), None, {}),
                (CheckPluginName('lnx_if'), u'2', {
                    'speed': 10000000,
                    'state': ['1']
                }),
                (CheckPluginName('if64'), u'00001001', {
                    'average': None,
                    'errors': (0.01, 0.1),
                    'speed': 1000000000,
                    'state': '1',
                    'traffic': (None, None),
                }),
            ],
        ),
        # Dict: Regular processing
        (
            u"""[
          {'check_plugin_name': 'df', 'item': u'/', 'parameters': {}, 'service_labels': {}},
          {'check_plugin_name': 'df', 'item': u'/xyz', 'parameters': "lala", 'service_labels': {u"x": u"y"}},
          {'check_plugin_name': 'df', 'item': u'/zzz', 'parameters': ['abc', 'xyz'], 'service_labels': {u"x": u"y"}},
          {'check_plugin_name': 'cpu.loads', 'item': None, 'parameters': cpuload_default_levels, 'service_labels': {u"x": u"y"}},
          {'check_plugin_name': 'chrony', 'item': None, 'parameters': {}, 'service_labels': {u"x": u"y"}},
          {'check_plugin_name': 'lnx_if', 'item': u'2', 'parameters': {'state': ['1'], 'speed': 10000000}, 'service_labels': {u"x": u"y"}},
        ]""",
            [
                (CheckPluginName('df'), u'/', {}),
                (CheckPluginName('df'), u'/xyz', "lala"),
                (CheckPluginName('df'), u'/zzz', ['abc', 'xyz']),
                (CheckPluginName('cpu_loads'), None, (5.0, 10.0)),
                (CheckPluginName('chrony'), None, {}),
                (CheckPluginName('lnx_if'), u'2', {
                    'speed': 10000000,
                    'state': ['1']
                }),
            ],
        ),
    ])
def test_parse_autochecks_file(config_check_variables, test_config, autochecks_content,
                               expected_result):
    autochecks_file = Path(cmk.utils.paths.autochecks_dir, "host.mk")
    with autochecks_file.open("w", encoding="utf-8") as f:
        f.write(autochecks_content)

    if expected_result is MKGeneralException:
        with pytest.raises(MKGeneralException):
            autochecks.parse_autochecks_file(
                "host",
                config.service_description,
                config_check_variables,
            )
        return

    parsed = autochecks.parse_autochecks_file(
        "host",
        config.service_description,
        config_check_variables,
    )
    assert len(parsed) == len(expected_result)

    for index, service in enumerate(parsed):
        expected = expected_result[index]
        assert service.check_plugin_name == expected[0]
        assert service.item == expected[1]
        assert service.parameters == expected[2], service.check_plugin_name


def test_has_autochecks():
    assert autochecks.has_autochecks("host") is False
    autochecks.save_autochecks_file("host", [])
    assert autochecks.has_autochecks("host") is True


def test_remove_autochecks_file():
    assert autochecks.has_autochecks("host") is False
    autochecks.save_autochecks_file("host", [])
    assert autochecks.has_autochecks("host") is True
    autochecks.remove_autochecks_file("host")
    assert autochecks.has_autochecks("host") is False


@pytest.mark.parametrize("items,expected_content", [
    ([], "[\n]\n"),
    ([
        discovery.Service(CheckPluginName('df'), u'/xyz', u"Filesystem /xyz", None,
                          DiscoveredServiceLabels(ServiceLabel(u"x", u"y"))),
        discovery.Service(CheckPluginName('df'), u'/', u"Filesystem /", {},
                          DiscoveredServiceLabels(ServiceLabel(u"x", u"y"))),
        discovery.Service(CheckPluginName('cpu_loads'), None, "CPU load", {},
                          DiscoveredServiceLabels(ServiceLabel(u"x", u"y"))),
    ], """[
  {'check_plugin_name': 'cpu_loads', 'item': None, 'parameters': {}, 'service_labels': {'x': 'y'}},
  {'check_plugin_name': 'df', 'item': '/', 'parameters': {}, 'service_labels': {'x': 'y'}},
  {'check_plugin_name': 'df', 'item': '/xyz', 'parameters': None, 'service_labels': {'x': 'y'}},
]\n"""),
])
def test_save_autochecks_file(items, expected_content):
    autochecks.save_autochecks_file("host", items)

    autochecks_file = Path(cmk.utils.paths.autochecks_dir, "host.mk")
    with autochecks_file.open("r", encoding="utf-8") as f:
        content = f.read()

    assert expected_content == content
