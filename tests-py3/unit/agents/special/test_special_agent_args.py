# -*- encoding: utf-8
import os
from typing import Dict  # pylint: disable=unused-import
from glob import glob
from argparse import Namespace
from importlib import import_module  # pylint: disable=import-error

import pytest  # type: ignore[import]
from testlib import cmk_path

REQUIRED_ARGUMENTS = {
    # TODO: add these as we migrate to py3
    'agent_aws': [
        '--access-key-id', 'ACCESS_KEY_ID', '--secret-access-key', 'SECRET_ACCESS_KEY',
        '--hostname', 'HOSTNAME'
    ],
    # 'agent_azure': [
    #     '--subscription', 'SUBSCRIPTION', '--client', 'CLIENT', '--tenant', 'TENANT', '--secret',
    #     'SECRET'
    # ],
    'agent_elasticsearch': ['HOSTNAME'],
    'agent_graylog': ['HOSTNAME'],
    'agent_jenkins': ['HOSTNAME'],
    'agent_jira': ['-P', 'PROTOCOL', '-u', 'USER', '-s', 'PASSWORD', '--hostname', 'HOSTNAME'],
    'agent_kubernetes': ['--token', 'TOKEN', '--infos', 'INFOS', 'HOST'],
    'agent_prometheus': [],
    'agent_splunk': ['HOSTNAME'],
    'agent_vsphere': ['HOSTNAME'],
    'agent_proxmox': ['HOSTNAME'],
}  # type: Dict


# TODO: this can be removed once all agents are py3
def _filter_python3_agents(agents):
    agents3 = []
    for agent_file in agents:
        with open(agent_file) as handle:
            shebang = next(handle)
        if shebang.strip().endswith("python3"):
            agents3.append(agent_file)

    assert len(agents3) < len(agents), "This helper function can be removed now"
    return agents3


def test_all_agents_tested():
    agent_files = glob("%s/cmk/special_agents/agent_*.py" % cmk_path())
    for agent_file in _filter_python3_agents(agent_files):
        name = os.path.basename(os.path.splitext(agent_file)[0])
        assert name in REQUIRED_ARGUMENTS, "Please add a test case for special agent: %r" % name


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
