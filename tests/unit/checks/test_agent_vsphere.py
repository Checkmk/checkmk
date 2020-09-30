#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({
        'tcp_port': 443,
        'direct': True,
        'skip_placeholder_vms': True,
        'ssl': False,
        'secret': 'secret',
        'spaces': 'cut',
        'user': 'username',
        'infos': ['hostsystem', 'virtualmachine', 'datastore', 'counters']
    }, [
        "-p", "443", "-u", "username", "-s", "secret", "-i",
        "hostsystem,virtualmachine,datastore,counters", "--direct", "--hostname", "host", "-P",
        "--spaces", "cut", "--no-cert-check", "address"
    ]),
    ({
        'tcp_port': 443,
        'host_pwr_display': None,
        'vm_pwr_display': None,
        'direct': True,
        'vm_piggyname': 'alias',
        'skip_placeholder_vms': True,
        'ssl': False,
        'secret': 'secret',
        'spaces': 'cut',
        'user': 'username',
        'infos': ['hostsystem', 'virtualmachine', 'datastore', 'counters']
    }, [
        "-p", "443", "-u", "username", "-s", "secret", "-i",
        "hostsystem,virtualmachine,datastore,counters", "--direct", "--hostname", "host", "-P",
        "--spaces", "cut", "--vm_piggyname", "alias", "--no-cert-check", "address"
    ]),
])
def test_vsphere_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_vsphere')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
