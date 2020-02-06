# -*- encoding: utf-8
import os

import pytest
from glob import glob

from argparse import Namespace
from importlib import import_module

from testlib import cmk_path

REQUIRED_ARGUMENTS = {
    'agent_azure': [
        '--subscription', 'SUBSCRIPTION', '--client', 'CLIENT', '--tenant', 'TENANT', '--secret',
        'SECRET'
    ],
    'agent_elasticsearch': ['HOSTNAME'],
    'agent_graylog': ['HOSTNAME'],
    'agent_jenkins': ['HOSTNAME'],
    'agent_jira': ['-P', 'PROTOCOL', '-u', 'USER', '-s', 'PASSWORD', '--hostname', 'HOSTNAME'],
    'agent_splunk': ['HOSTNAME'],
    'agent_vsphere': ['HOSTNAME'],
}


@pytest.mark.parametrize("agent_name, required_args", REQUIRED_ARGUMENTS.items())
def test_parse_arguments(agent_name, required_args):
    agent = import_module("cmk.special_agents.%s" % agent_name)

    parse_arguments = getattr(agent, 'parse_arguments')

    msg = "Special agents should process their arguments in a function called parse_arguments!"
    assert callable(parse_arguments), msg

    msg = "Special agents' parse_arguments should return the created argparse.Namespace"
    assert isinstance(parse_arguments(required_args), Namespace), msg

    msg = "Special agents should support the argument '--debug'"
    # This also ensures that the parse_arguments function indeed expects
    # sys.argv[1:], i.e. the first element omitted.
    assert parse_arguments(['--debug'] + required_args).debug is True, msg
