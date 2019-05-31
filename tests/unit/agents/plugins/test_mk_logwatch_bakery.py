import imp
import importlib
import os
import sys

import pytest

from testlib import cmk_path, repo_path


def test_get_logfiles_config_lines():
    # Workaround to make bakelet available in the test, needs to be executed in the test scope.
    bakelet = 'mk_logwatch'
    path = os.path.join(cmk_path(), 'enterprise', 'agents', 'bakery', bakelet)
    with open(path, "r") as f:
        source = f.read()
    extended_source = 'from cmk_base.cee.agent_bakery_plugins import bakery_info' + '\n' + source
    exec (extended_source)

    config = [
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
    ]

    actual_result = _get_logfiles_config_lines(config)
    assert actual_result == [
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
    ]
