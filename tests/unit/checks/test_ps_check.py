import pytest
import ast
from testlib import cmk_path

# Mark all tests in this file as check related tests
pytestmark = pytest.mark.checks

ps_parsed = [
    [None, ('root', '1', '2', '00:00:00/3-00:00:00', '4'), '123foobar'],
    [None, ('root', '1', '2', '00:00:00/3-00:00:00', '4'), 'ab_foo'],
    [None, ('root', '1', '2', '00:00:00/3-00:00:00', '4'), '23_foo'],
    [None, ('root', '1', '2', '00:00:00/3-00:00:00', '4'), 'xy_foo'],
    [None, ('root', '1', '2', '00:00:00/3-00:00:00', '4'), 'c:\\123_foo'],
    [None, ('root', '1', '2', '00:00:00/3-00:00:00', '4'), 'a/b/123_foo'],
]


@pytest.mark.parametrize("parsed,discovery_rules,result", [
    (ps_parsed, [], []),
    (ps_parsed, [({'descr': 'FOO', 'match': '~.*_foo'}, [], ['@all'], {})],
     [('FOO', {'process': '~.*_foo', 'match_groups': (), 'user': None})]),
    (ps_parsed, [({'descr': 'FOO %s', 'match': '~(.*)_foo'}, [], ['@all'], {})],
     [('FOO ab', {'process': '~(.*)_foo', 'match_groups': ('ab',), 'user': None}),
      ('FOO 23', {'process': '~(.*)_foo', 'match_groups': ('23',), 'user': None}),
      ('FOO xy', {'process': '~(.*)_foo', 'match_groups': ('xy',), 'user': None}),
      ('FOO c:\\123', {'process': '~(.*)_foo', 'match_groups': ('c:\\123',), 'user': None}),
      ('FOO a/b/123', {'process': '~(.*)_foo', 'match_groups': ('a/b/123',), 'user': None}),
     ]),
    (ps_parsed, [({'descr': 'FOO %s %s', 'match': '~(.*)_(f)oo'}, [], ['@all'], {})],
     [('FOO ab f', {'process': '~(.*)_(f)oo', 'match_groups': ('ab', 'f'), 'user': None}),
      ('FOO 23 f', {'process': '~(.*)_(f)oo', 'match_groups': ('23', 'f'), 'user': None}),
      ('FOO xy f', {'process': '~(.*)_(f)oo', 'match_groups': ('xy', 'f'), 'user': None}),
      ('FOO c:\\123 f', {'process': '~(.*)_(f)oo', 'match_groups': ('c:\\123', 'f'), 'user': None}),
      ('FOO a/b/123 f', {'process': '~(.*)_(f)oo', 'match_groups': ('a/b/123', 'f'), 'user': None}),
     ]),
    # Special chars: '\' (windows) vs. '/' (linux)
    (ps_parsed, [({'descr': 'FOO %s', 'match': '~c:\\\\(.*)_foo'}, [], ['@all'], {})],
     [('FOO 123', {'process': '~c:\\\\(.*)_foo', 'match_groups': ('123',), 'user': None}),
     ]),
    (ps_parsed, [({'descr': 'FOO %s %s', 'match': '~c:\\\\(.*)_(f)oo'}, [], ['@all'], {})],
     [('FOO 123 f', {'process': '~c:\\\\(.*)_(f)oo', 'match_groups': ('123', 'f'), 'user': None}),
     ]),
    (ps_parsed, [({'descr': 'FOO %s', 'match': '~a/b/(.*)_foo'}, [], ['@all'], {})],
     [('FOO 123', {'process': '~a/b/(.*)_foo', 'match_groups': ('123',), 'user': None}),
     ]),
    (ps_parsed, [({'descr': 'FOO %s %s', 'match': '~a/b/(.*)_(f)oo'}, [], ['@all'], {})],
     [('FOO 123 f', {'process': '~a/b/(.*)_(f)oo', 'match_groups': ('123', 'f'), 'user': None}),
     ]),
    # Too little amount of '%s'
    (ps_parsed, [({'descr': 'FOO %s', 'match': '~(.*)_(f)oo'}, [], ['@all'], {})],
     [('FOO ab', {'process': '~(.*)_(f)oo', 'match_groups': ('ab', 'f'), 'user': None}),
      ('FOO 23', {'process': '~(.*)_(f)oo', 'match_groups': ('23', 'f'), 'user': None}),
      ('FOO xy', {'process': '~(.*)_(f)oo', 'match_groups': ('xy', 'f'), 'user': None}),
      ('FOO c:\\123', {'process': '~(.*)_(f)oo', 'match_groups': ('c:\\123', 'f'), 'user': None}),
      ('FOO a/b/123', {'process': '~(.*)_(f)oo', 'match_groups': ('a/b/123', 'f'), 'user': None}),
     ]),
    (ps_parsed, [({'descr': 'FOO %s', 'match': '~c:\\\\(.*)_(f)oo'}, [], ['@all'], {})],
     [('FOO 123', {'process': '~c:\\\\(.*)_(f)oo', 'match_groups': ('123', 'f'), 'user': None}),
     ]),
    (ps_parsed, [({'descr': 'FOO %s', 'match': '~a/b/(.*)_(f)oo'}, [], ['@all'], {})],
     [('FOO 123', {'process': '~a/b/(.*)_(f)oo', 'match_groups': ('123', 'f'), 'user': None}),
     ]),
])
def test_ps_discovery(check_manager, monkeypatch, parsed, discovery_rules, result):
    check = check_manager.get_check("ps")
    monkeypatch.setitem(check.context, "inventory_processes", [])
    monkeypatch.setitem(check.context, "inventory_processes_rules", discovery_rules)
    discovery_result = check.run_discovery(((1, parsed), None, None, None, None))
    assert discovery_result == result


default_params = {'levels': (1, 1, 99999, 99999)}


@pytest.mark.parametrize("params,parsed,count_processes_str", [
    ({}, ps_parsed, 6),
    # Old
    ({'process': '~.*_bar'}, ps_parsed, 0),
    ({'process': '~.*_foo'}, ps_parsed, 5),
    ({'process': '~(.*)_bar'}, ps_parsed, 0),
    ({'process': '~(.*)_foo'}, ps_parsed, 5),
    # New
    ({'process': '~.*_bar', 'match_groups': []}, ps_parsed, 0),
    ({'process': '~.*_foo', 'match_groups': []}, ps_parsed, 5),
    ({'process': '~(.*)_bar', 'match_groups': []}, ps_parsed, 0),
    ({'process': '~(.*)_foo', 'match_groups': ['ab']}, ps_parsed, 1),
    ({'process': '~(.*)_foo', 'match_groups': ['23']}, ps_parsed, 1),
    ({'process': '~(.*)_foo', 'match_groups': ['xy']}, ps_parsed, 1),
    ({'process': '~c:\\\\(.*)_foo', 'match_groups': ['123']}, ps_parsed, 1),
    ({'process': '~a/b/(.*)_foo', 'match_groups': ['123']}, ps_parsed, 1),
])
def test_ps_check(check_manager, monkeypatch, params, parsed, count_processes_str):
    check = check_manager.get_check("ps")
    params.update(default_params)
    check_result = check.run_check('', params, ((1, parsed), None, None, None, None))
    _state, infotext, _perfdata = check_result
    assert infotext.startswith('%s processes' % count_processes_str)
