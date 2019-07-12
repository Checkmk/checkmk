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
        # Handle old format
        (u"""[
  ('hostxyz', 'df', '/', {}),
]""", [
            ('df', u'/', {
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
        # Convert non unicode item
        (
            u"""[
  ('df', '/', {}),
]""",
            [
                ('df', u'/', {
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
        # Allow non string items
        (
            u"""[
  ('df', 123, {}),
]""",
            [
                ('df', 123, {
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
        # Exception on invalid check type
        (
            u"""[
  (123, 'abc', {}),
]""",
            MKGeneralException,
        ),
        # Regular processing
        (
            u"""[
  ('df', u'/', {}),
  ('cpu.loads', None, cpuload_default_levels),
  ('chrony', None, {}),
  ('lnx_if', u'2', {'state': ['1'], 'speed': 10000000}),
]""",
            [
                ('df', u'/', {
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
                ('cpu.loads', None, (5.0, 10.0)),
                ('chrony', None, {
                    'alert_delay': (300, 3600),
                    'ntp_levels': (10, 200.0, 500.0)
                }),
                ('lnx_if', u'2', {
                    'errors': (0.01, 0.1),
                    'speed': 10000000,
                    'state': ['1']
                }),
            ],
        ),
    ])
def test_read_autochecks_of(test_config, autochecks_content, expected_result):
    autochecks_file = Path(cmk.utils.paths.autochecks_dir).joinpath("host.mk")
    with autochecks_file.open("w", encoding="utf-8") as f:  # pylint: disable=no-member
        f.write(autochecks_content)

    if expected_result is MKGeneralException:
        with pytest.raises(MKGeneralException):
            autochecks.read_autochecks_of("host")
        return

    result = autochecks.read_autochecks_of("host")
    assert result == expected_result

    # Check that all items are unicode strings
    assert all(not isinstance(e[1], str) for e in result)


def test_parse_autochecks_file_not_existing():
    assert autochecks.parse_autochecks_file("host") == []


@pytest.mark.parametrize(
    "autochecks_content,expected_result",
    [
        (u"[]", []),
        (u"", []),
        (u"@", MKGeneralException),
        (u"[abc123]", []),
        # Handle old format
        (u"""[
  ('hostxyz', 'df', '/', {}),
]""", [
            ('df', u'/', '{}'),
        ]),
        # Convert non unicode item
        (
            u"""[
          ('df', '/', {}),
        ]""",
            [
                ('df', u'/', "{}"),
            ],
        ),
        # Allow non string items
        (
            u"""[
          ('df', 123, {}),
        ]""",
            [
                ('df', 123, "{}"),
            ],
        ),
        # Regular processing
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

        if isinstance(service.paramstr, str) and service.paramstr.startswith("{"):
            # Work around random dict key sorting
            assert ast.literal_eval(service.paramstr) == ast.literal_eval(expected[2])
        else:
            assert service.paramstr == expected[2]


def test_has_autochecks():
    assert discovery._has_autochecks("host") is False
    discovery._save_autochecks_file("host", [])
    assert discovery._has_autochecks("host") is True


def test_remove_autochecks_file():
    assert discovery._has_autochecks("host") is False
    discovery._save_autochecks_file("host", [])
    assert discovery._has_autochecks("host") is True
    discovery._remove_autochecks_file("host")
    assert discovery._has_autochecks("host") is False


@pytest.mark.parametrize("items,expected_content", [
    ([], "[\n]\n"),
    ([
        discovery.DiscoveredService('df', u'/xyz', u"Filesystem /xyz", "None"),
        discovery.DiscoveredService('df', u'/', u"Filesystem /", "{}"),
        discovery.DiscoveredService('cpu.loads', None, "CPU load", "cpuload_default_levels"),
    ], """[
  ('cpu.loads', None, cpuload_default_levels),
  ('df', u'/', {}),
  ('df', u'/xyz', None),
]\n"""),
])
def test_save_autochecks_file(items, expected_content):
    discovery._save_autochecks_file("host", items)

    autochecks_file = Path(cmk.utils.paths.autochecks_dir).joinpath("host.mk")
    with autochecks_file.open("r", encoding="utf-8") as f:  # pylint: disable=no-member
        content = f.read()

    assert expected_content == content
