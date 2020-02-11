# pylint: disable=redefined-outer-name
import pytest  # type: ignore[import]
from pathlib2 import Path
import six

from testlib import CheckManager
# TODO: Why is the suppression necessary?
from testlib.base import Scenario  # type: ignore[import]

import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException

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
    CheckManager().load(["df", "cpu", "chrony", "lnx_if"])
    ts = Scenario().add_host("host")
    return ts.apply(monkeypatch)


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
                    'df', '123', u"", {
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
        # Dict: Regular processing
        (
            u"""[
  {'check_plugin_name': 'df', 'item': u'/', 'parameters': {}, 'service_labels': {}},
  {'check_plugin_name': 'cpu.loads', 'item': None, 'parameters': cpuload_default_levels, 'service_labels': {}},
  {'check_plugin_name': 'chrony', 'item': None, 'parameters': {}, 'service_labels': {}},
  {'check_plugin_name': 'lnx_if', 'item': u'2', 'parameters': {'state': ['1'], 'speed': 10000000}, 'service_labels': {}},
]""",
            [
                Service(
                    'df', u'/', u"", {
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
                Service('cpu.loads', None, u"", (5.0, 10.0)),
                Service('chrony', None, u"", {
                    'alert_delay': (300, 3600),
                    'ntp_levels': (10, 200.0, 500.0)
                }),
                Service('lnx_if', u'2', u"", {
                    'errors': (0.01, 0.1),
                    'speed': 10000000,
                    'state': ['1']
                }),
            ],
        ),
    ])
def test_manager_get_autochecks_of(test_config, autochecks_content, expected_result):
    autochecks_file = Path(cmk.utils.paths.autochecks_dir, "host.mk")
    with autochecks_file.open("w", encoding="utf-8") as f:  # pylint: disable=no-member
        f.write(autochecks_content)

    manager = test_config._autochecks_manager

    if expected_result is MKGeneralException:
        with pytest.raises(MKGeneralException):
            manager.get_autochecks_of("host", config.compute_check_parameters,
                                      config.service_description, config.get_check_variables)
        return

    result = manager.get_autochecks_of("host", config.compute_check_parameters,
                                       config.service_description, config.get_check_variables)
    assert result == expected_result

    # Check that the ConfigCache method also returns the correct data
    assert test_config.get_autochecks_of("host") == result

    # Check that there are no str items (None, int, ...)
    assert all(not isinstance(s.item, str) for s in result)
    # All desriptions need to be unicode
    assert all(isinstance(s.description, six.text_type) for s in result)


def test_parse_autochecks_file_not_existing():
    assert autochecks.parse_autochecks_file("host", config.service_description) == []


@pytest.mark.parametrize(
    "autochecks_content,expected_result",
    [
        (u"[]", []),
        (u"", []),
        (u"@", MKGeneralException),
        (u"[abc123]", []),
        # Tuple: Handle old format
        (u"""[
  ('hostxyz', 'df', '/', {}),
]""", [
            ('df', u'/', '{}'),
        ]),
        # Tuple: Convert non unicode item
        (
            u"""[
          ('df', '/', {}),
        ]""",
            [
                ('df', u'/', "{}"),
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
                ('df', u'/', '{}'),
                ('df', u'/xyz', "'lala'"),
                ('df', u'/zzz', "['abc', 'xyz']"),
                ('cpu.loads', None, 'cpuload_default_levels'),
                ('chrony', None, '{}'),
                ('lnx_if', u'2', "{'speed': 10000000, 'state': ['1']}"),
                ('if64', u'00001001',
                 "{'average': if_default_average, 'errors': if_default_error_levels, 'speed': 1000000000, 'state': '1', 'traffic': if_default_traffic_levels}"
                ),
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
                ('df', u'/', '{}'),
                ('df', u'/xyz', "'lala'"),
                ('df', u'/zzz', "['abc', 'xyz']"),
                ('cpu.loads', None, 'cpuload_default_levels'),
                ('chrony', None, '{}'),
                ('lnx_if', u'2', "{'speed': 10000000, 'state': ['1']}"),
            ],
        ),
    ])
def test_parse_autochecks_file(test_config, autochecks_content, expected_result):
    autochecks_file = Path(cmk.utils.paths.autochecks_dir, "host.mk")
    with autochecks_file.open("w", encoding="utf-8") as f:  # pylint: disable=no-member
        f.write(autochecks_content)

    if expected_result is MKGeneralException:
        with pytest.raises(MKGeneralException):
            autochecks.parse_autochecks_file("host", config.service_description)
        return

    parsed = autochecks.parse_autochecks_file("host", config.service_description)
    assert len(parsed) == len(expected_result)

    for index, service in enumerate(parsed):
        expected = expected_result[index]
        assert service.check_plugin_name == expected[0]
        assert service.item == expected[1]
        assert service.parameters_unresolved == expected[2]


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
        discovery.DiscoveredService('df', u'/xyz', u"Filesystem /xyz", "None",
                                    DiscoveredServiceLabels(ServiceLabel(u"x", u"y"))),
        discovery.DiscoveredService('df', u'/', u"Filesystem /", "{}",
                                    DiscoveredServiceLabels(ServiceLabel(u"x", u"y"))),
        discovery.DiscoveredService('cpu.loads', None, "CPU load", "cpuload_default_levels",
                                    DiscoveredServiceLabels(ServiceLabel(u"x", u"y"))),
    ], """[
  {'check_plugin_name': 'cpu.loads', 'item': None, 'parameters': cpuload_default_levels, 'service_labels': {u'x': u'y'}},
  {'check_plugin_name': 'df', 'item': u'/', 'parameters': {}, 'service_labels': {u'x': u'y'}},
  {'check_plugin_name': 'df', 'item': u'/xyz', 'parameters': None, 'service_labels': {u'x': u'y'}},
]\n"""),
])
def test_save_autochecks_file(items, expected_content):
    autochecks.save_autochecks_file("host", items)

    autochecks_file = Path(cmk.utils.paths.autochecks_dir, "host.mk")
    with autochecks_file.open("r", encoding="utf-8") as f:  # pylint: disable=no-member
        content = f.read()

    assert expected_content == content
