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
    exec(extended_source, bakelet.__dict__)  # yapf: disable
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
            'context': False,
            'logfiles': ['/var/log/*.log', '/omd/sites/*/var/log/*.log'],
            'overflow': 'C',
            'fromstart': True,
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
        },
    ], [
        '',
        '/var/log/*.log /omd/sites/*/var/log/*.log overflow=C nocontext=True fromstart=True',
        ' C foo',
        ' W BAR',
        ' O .*',
        '',
        '/etc/* maxlines=5000 maxtime=20 overflow=W maxfilesize=1024 maxlinesize=100',
        ' I .*',
    ]),
])
def test_get_file_section_lines(bakelet, config, expected):
    section_lines = bakelet._get_file_section_lines(config)
    assert section_lines == expected


@pytest.mark.parametrize('config, expected', [
    ([
        {
            'name': 'my_cluster',
            'ips': ['192.168.1.1', '192.168.1.2']
        },
        {
            'name': 'another_cluster',
            'ips': ['192.168.2.1', '192.168.1.2', '192.168.1.3', '192.168.1.4']
        },
    ], [
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
def test_get_cluster_section_lines(bakelet, config, expected):
    cluster_lines = bakelet._get_cluster_section_lines(config)
    assert cluster_lines == expected
