# pylint: disable=redefined-outer-name
import ast
import pytest  # type: ignore

from pathlib2 import Path
from testlib.base import Scenario

import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException

import cmk_base.config as config
import cmk_base.check_api as check_api
import cmk_base.autochecks as autochecks
import cmk_base.discovery as discovery
from cmk_base.check_utils import Service
from cmk_base.discovered_labels import (
    DiscoveredServiceLabels,
    ServiceLabel,
)


@pytest.fixture(autouse=True)
def autochecks_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(cmk.utils.paths, "autochecks_dir", str(tmp_path))


@pytest.fixture()
def test_config(monkeypatch):
    config.load_checks(check_api.get_check_api_context,
                       ["checks/df", "checks/cpu", "checks/chrony", "checks/lnx_if"])

    ts = Scenario().add_host("host")
    return ts.apply(monkeypatch)


@pytest.mark.parametrize(
    "autochecks_content,expected_result",
    [
        (u"[]", []),
        (u"", []),
        (u"@", []),
        (u"[abc123]", []),
        # Tuple: Handle old format
        (u"""[
  ('hostxyz', 'df', '/', {}),
]""", [
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
        ]),
        # Tuple: Convert non unicode item
        (
            u"""[
  ('df', '/', {}),
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
            ],
        ),
        # Tuple: Allow non string items
        (
            u"""[
  ('df', 123, {}),
]""",
            [
                Service(
                    'df', 123, u"", {
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
        # Tuple: Exception on invalid check type
        (
            u"""[
  (123, 'abc', {}),
]""",
            MKGeneralException,
        ),
        # Tuple: Regular processing
        (
            u"""[
  ('df', u'/', {}),
  ('cpu.loads', None, cpuload_default_levels),
  ('chrony', None, {}),
  ('lnx_if', u'2', {'state': ['1'], 'speed': 10000000}),
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
        # Dict: Allow non string items
        (
            u"""[
  {'check_plugin_name': 'df', 'item': 123, 'parameters': {}, 'service_labels': {}},
]""",
            [
                Service(
                    'df', 123, u"", {
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
    autochecks_file = Path(cmk.utils.paths.autochecks_dir).joinpath("host.mk")
    with autochecks_file.open("w", encoding="utf-8") as f:  # pylint: disable=no-member
        f.write(autochecks_content)

    manager = test_config._autochecks_manager

    if expected_result is MKGeneralException:
        with pytest.raises(MKGeneralException):
            manager.get_autochecks_of("host")
        return

    result = manager.get_autochecks_of("host")
    assert result == expected_result

    # Check that the ConfigCache method also returns the correct data
    assert test_config.get_autochecks_of("host") == result

    # Check that there are no str items (None, int, ...)
    assert all(not isinstance(s.item, str) for s in result)
    # All desriptions need to be unicode
    assert all(isinstance(s.description, unicode) for s in result)


def test_parse_autochecks_file_not_existing():
    assert autochecks.parse_autochecks_file("host") == []


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
        # Tuple: Allow non string items
        (
            u"""[
          ('df', 123, {}),
        ]""",
            [
                ('df', 123, "{}"),
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
        ]""",
            [
                ('df', u'/', '{}'),
                ('df', u'/xyz', "'lala'"),
                ('df', u'/zzz', "['abc', 'xyz']"),
                ('cpu.loads', None, 'cpuload_default_levels'),
                ('chrony', None, '{}'),
                ('lnx_if', u'2', "{'state': ['1'], 'speed': 10000000}"),
            ],
        ),
        # Dict: Allow non string items
        (
            u"""[
          {'check_plugin_name': 'df', 'item': 123, 'parameters': {}, 'service_labels': {}},
        ]""",
            [
                ('df', 123, "{}"),
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
                ('lnx_if', u'2', "{'state': ['1'], 'speed': 10000000}"),
            ],
        ),
    ])
def test_parse_autochecks_file(test_config, autochecks_content, expected_result):
    autochecks_file = Path(cmk.utils.paths.autochecks_dir).joinpath("host.mk")
    with autochecks_file.open("w", encoding="utf-8") as f:  # pylint: disable=no-member
        f.write(autochecks_content)

    if expected_result is MKGeneralException:
        with pytest.raises(MKGeneralException):
            autochecks.parse_autochecks_file("host")
        return

    parsed = autochecks.parse_autochecks_file("host")
    assert len(parsed) == len(expected_result)

    for index, service in enumerate(parsed):
        expected = expected_result[index]
        assert service.check_plugin_name == expected[0]
        assert service.item == expected[1]

        if isinstance(service.parameters_unresolved,
                      str) and service.parameters_unresolved.startswith("{"):
            # Work around random dict key sorting
            assert ast.literal_eval(service.parameters_unresolved) == ast.literal_eval(expected[2])
        else:
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

    autochecks_file = Path(cmk.utils.paths.autochecks_dir).joinpath("host.mk")
    with autochecks_file.open("r", encoding="utf-8") as f:  # pylint: disable=no-member
        content = f.read()

    assert expected_content == content
