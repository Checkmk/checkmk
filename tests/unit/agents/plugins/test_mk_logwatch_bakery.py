# pylint: disable=redefined-outer-name,protected-access
import imp
import os

import pytest

from testlib import cmk_path

DICT1 = {'id': 1}

DICT2 = {'id': 1}


@pytest.fixture(scope="module")
def bakelet(request):
    """
      Fixture to inject bakelet as module
      """
    path = os.path.join(cmk_path(), 'enterprise', 'agents', 'bakery', 'mk_logwatch')
    with open(path, "r") as handle:
        source = handle.read()
    extended_source = 'from cmk_base.cee.agent_bakery_plugins import bakery_info' + '\n' + source

    bakelet = imp.new_module('bakelet')
    exec extended_source in bakelet.__dict__
    yield bakelet


@pytest.mark.parametrize('configs, applicable', [
    ([], (False, [])),
    ([True, DICT1], (True, [])),
    ([None, DICT1], (False, [])),
    ([DICT1, True], (True, [DICT1])),
    ([DICT1, None, DICT2], (True, [DICT1])),
    ([DICT1, True, DICT2], (True, [DICT1])),
    ([DICT1, DICT2], (True, [DICT1, DICT2])),
])
def test_get_applicable_configs(bakelet, configs, applicable):
    assert applicable == bakelet._get_applicable_rule_values(configs)


@pytest.mark.parametrize('config, expected', [
    ([
        {
            'context': True,
            'logfiles': ['/var/log/*.log', '/omd/sites/*/var/log/*.log'],
            'overflow': 'C',
            'patterns': [('C', u'foo'), ('W', u'BAR'), ('O', u'')]
        },
        {
            'context': True,
            'logfiles': ['/etc/*'],
            'maxfilesize': 1024,
            'maxlines': 5000,
            'maxlinesize': 100,
            'maxtime': 20,
            'overflow': 'W',
            'patterns': [('I', u'.*')],
            'cluster': [
                {
                    'name': 'my_cluster',
                    'ips': ['192.168.1.1', '192.168.1.2']
                },
                {
                    'name': 'another_cluster',
                    'ips': ['192.168.2.1', '192.168.1.2', '192.168.1.3', '192.168.1.4']
                },
            ]
        },
    ], [
        '',
        '/var/log/*.log /omd/sites/*/var/log/*.log overflow=C',
        ' C foo',
        ' W BAR',
        ' O .*',
        '',
        '/etc/* maxlines=5000 maxtime=20 overflow=W maxfilesize=1024 maxlinesize=100',
        ' I .*',
        '',
        'CLUSTER my_cluster',
        ' 192.168.1.1',
        ' 192.168.1.2',
        '',
        'CLUSTER another_cluster',
        ' 192.168.2.1',
        ' 192.168.1.2',
        ' 192.168.1.3',
        ' 192.168.1.4',
    ]),
])
def test_get_logfiles_config_lines(bakelet, config, expected):
    assert bakelet._get_logfiles_config_lines(config) == expected
