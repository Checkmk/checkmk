#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from argparse import Namespace
from glob import glob
import os
from typing import Dict, List
from importlib import import_module

import pytest  # type: ignore[import]
from testlib import cmk_path

# TODO: Actually fix this stuff.
NOT_TESTED_YET = {
    'agent_3par',
    'agent_activemq',
    'agent_appdynamics',
    'agent_bi',
    'agent_ddn_s2a',
    'agent_emcvnx',
    'agent_hp_msa',
    'agent_innovaphone',
    'agent_ipmi_sensors',
    'agent_jolokia',
    'agent_netapp',
    'agent_prism',
    'agent_random',
    'agent_ruckus_spot',
    'agent_salesforce',
    'agent_siemens_plc',
    'agent_storeonce',
    'agent_tinkerforge',
    'agent_ucs_bladecenter',
    'agent_vnx_quotas',
    'agent_zerto',
}

# TODO: Actually fix this stuff.
AGENTS_WITHOUT_PARSE_ARGUMENTS = {
    'agent_allnet_ip_sensoric',
    'agent_fritzbox',
    'agent_hivemanager',
    'agent_hivemanager_ng',
    'agent_ibmsvc',
}

REQUIRED_ARGUMENTS: Dict[str, List[str]] = {
    'agent_allnet_ip_sensoric': ['HOSTNAME'],
    'agent_aws': [
        '--access-key-id', 'ACCESS_KEY_ID', '--secret-access-key', 'SECRET_ACCESS_KEY',
        '--hostname', 'HOSTNAME'
    ],
    'agent_azure': [
        '--subscription', 'SUBSCRIPTION', '--client', 'CLIENT', '--tenant', 'TENANT', '--secret',
        'SECRET'
    ],
    'agent_couchbase': ['HOSTNAME'],
    'agent_elasticsearch': ['HOSTNAME'],
    'agent_fritzbox': ['HOSTNAME'],
    'agent_graylog': ['HOSTNAME'],
    'agent_hivemanager': ['IP', 'USER', 'PASSWORD'],
    'agent_hivemanager_ng': [
        'URL', 'VHM_ID', 'API_TOKEN', 'CLIENT_ID', 'CLIENT_SECRET', 'REDIRECT_URL'
    ],
    'agent_ibmsvc': ['HOSTNAME'],
    'agent_jenkins': ['HOSTNAME'],
    'agent_jira': ['-P', 'PROTOCOL', '-u', 'USER', '-s', 'PASSWORD', '--hostname', 'HOSTNAME'],
    'agent_kubernetes': ['--token', 'TOKEN', '--infos', 'INFOS', 'HOST'],
    'agent_prometheus': [],
    'agent_rabbitmq': [
        '-P', 'PROTOCOL', '-m', 'SECTIONS', '-u', 'USER', '-s', 'PASSWORD', '--hostname', 'HOSTNAME'
    ],
    'agent_splunk': ['HOSTNAME'],
    'agent_vsphere': ['HOSTNAME'],
    'agent_proxmox': ['HOSTNAME'],
    'agent_storeonce4x': ['USER', 'PASSWORD', 'HOST'],
    'agent_cisco_prime': ['--hostname', 'HOSTNAME'],
}


def test_all_agents_tested():
    agents = {
        os.path.basename(os.path.splitext(agent_file)[0])
        for agent_file in glob("%s/cmk/special_agents/agent_*.py" % cmk_path())
    }
    untested = agents - set(REQUIRED_ARGUMENTS) - NOT_TESTED_YET
    assert not untested, "Please add test cases for special agents %s" % untested


@pytest.mark.parametrize("agent_name, required_args", list(REQUIRED_ARGUMENTS.items()))
def test_parse_arguments(agent_name, required_args):
    agent = import_module("cmk.special_agents.%s" % agent_name)
    if agent_name in AGENTS_WITHOUT_PARSE_ARGUMENTS:
        return

    parse_arguments = getattr(agent, 'parse_arguments')

    msg = "Special agents should process their arguments in a function called parse_arguments!"
    assert callable(parse_arguments), msg

    msg = "Special agents' parse_arguments should return the created argparse.Namespace"
    assert isinstance(parse_arguments(required_args), Namespace), msg

    msg = "Special agents should support the argument '--debug'"
    # This also ensures that the parse_arguments function indeed expects
    # sys.argv[1:], i.e. the first element omitted.
    assert parse_arguments(['--debug'] + required_args).debug is True, msg
