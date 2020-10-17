#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
import pytest  # type: ignore[import]

from cmk.base.check_legacy_includes.legacy_docker import *

pytestmark = pytest.mark.checks

regex = re.compile


@pytest.mark.parametrize('indata,outdata', [
    ([], []),
    ([
        ['   ['],
        ['    {'],
        ['        "Name": "bridge",'],
        ['        "Id": "b9cfbb124f4640cc93cf92fdc687cb219ff000ef1eb18d01365ccf190544a44c",'],
        ['        "Created": "2018-10-09T07:46:46.432508166+02:00",'],
        ['        "Scope": "local",'],
        ['        "Driver": "bridge",'],
        ['        "EnableIPv6": false,'],
        ['        "IPAM": {'],
        ['            "Driver": "default",'],
        ['            "Options": null,'],
        ['            "Config": ['],
        ['                {'],
        ['                    "Subnet": "172.17.0.0/16",'],
        ['                    "Gateway": "172.17.0.1"'],
        ['                }'],
        ['            ]'],
        ['        },'],
        ['        "Internal": false,'],
        ['        "Attachable": false,'],
        ['        "Ingress": false,'],
        ['        "ConfigFrom": {'],
        ['            "Network": ""'],
        ['        },'],
        ['        "ConfigOnly": false,'],
        ['        "Containers": {'],
        ['            "b58b7b9d1cdebc7d596916d8d48f5053571731cf3c470fed9b0ff0dca0eac869": {'],
        ['                "Name": "monitoring",'],
        [
            '                "EndpointID": "63eff84573fa771b1029166b3b110283d076ff46b7faa7241e394ce3626becbc",'
        ],
        ['                "MacAddress": "02:42:ac:11:00:02",'],
        ['                "IPv4Address": "172.17.0.2/16",'],
        ['                "IPv6Address": ""'],
        ['            }'],
        ['        },'],
        ['        "Options": {'],
        ['            "com.docker.network.bridge.default_bridge": "true",'],
        ['            "com.docker.network.bridge.enable_icc": "true",'],
        ['            "com.docker.network.bridge.enable_ip_masquerade": "true",'],
        ['            "com.docker.network.bridge.host_binding_ipv4": "0.0.0.0",'],
        ['            "com.docker.network.bridge.name": "docker0",'],
        ['            "com.docker.network.driver.mtu": "1500"'],
        ['        },'],
        ['        "Labels": {}'],
        ['    },'],
        ['    {'],
        ['        "Name": "example.com",'],
        ['        "Id": "40a17e390f71cb60f4815cb7f57341a621645bcf912680e658f0bbf89709fae4",'],
        ['        "Created": "2018-05-20T09:48:58.39451255+02:00",'],
        ['        "Scope": "local",'],
        ['        "Driver": "bridge",'],
        ['        "EnableIPv6": false,'],
        ['        "IPAM": {'],
        ['            "Driver": "default",'],
        ['            "Options": {},'],
        ['            "Config": ['],
        ['                {'],
        ['                    "Subnet": "10.5.0.0/24",'],
        ['                    "IPRange": "10.5.0.0/24",'],
        ['                    "Gateway": "10.5.0.254"'],
        ['                }'],
        ['            ]'],
        ['        },'],
        ['        "Internal": false,'],
        ['        "Attachable": false,'],
        ['        "Ingress": false,'],
        ['        "ConfigFrom": {'],
        ['            "Network": ""'],
        ['        },'],
        ['        "ConfigOnly": false,'],
        ['        "Containers": {},'],
        ['        "Options": {},'],
        ['        "Labels": {}'],
        ['    }'],
        [']'],
    ], [{
        "Name": "bridge",
        "Id": "b9cfbb124f4640cc93cf92fdc687cb219ff000ef1eb18d01365ccf190544a44c",
        "Created": "2018-10-09T07:46:46.432508166+02:00",
        "Scope": "local",
        "Driver": "bridge",
        "EnableIPv6": False,
        "IPAM": {
            "Driver": "default",
            "Options": None,
            "Config": [{
                "Subnet": "172.17.0.0/16",
                "Gateway": "172.17.0.1"
            }]
        },
        "Internal": False,
        "Attachable": False,
        "Ingress": False,
        "ConfigFrom": {
            "Network": ""
        },
        "ConfigOnly": False,
        "Containers": {
            "b58b7b9d1cdebc7d596916d8d48f5053571731cf3c470fed9b0ff0dca0eac869": {
                "Name": "monitoring",
                "EndpointID": "63eff84573fa771b1029166b3b110283d076ff46b7faa7241e394ce3626becbc",
                "MacAddress": "02:42:ac:11:00:02",
                "IPv4Address": "172.17.0.2/16",
                "IPv6Address": ""
            }
        },
        "Options": {
            "com.docker.network.bridge.default_bridge": "true",
            "com.docker.network.bridge.enable_icc": "true",
            "com.docker.network.bridge.enable_ip_masquerade": "true",
            "com.docker.network.bridge.host_binding_ipv4": "0.0.0.0",
            "com.docker.network.bridge.name": "docker0",
            "com.docker.network.driver.mtu": "1500"
        },
        "Labels": {}
    }, {
        "Name": "example.com",
        "Id": "40a17e390f71cb60f4815cb7f57341a621645bcf912680e658f0bbf89709fae4",
        "Created": "2018-05-20T09:48:58.39451255+02:00",
        "Scope": "local",
        "Driver": "bridge",
        "EnableIPv6": False,
        "IPAM": {
            "Driver": "default",
            "Options": {},
            "Config": [{
                "Subnet": "10.5.0.0/24",
                "IPRange": "10.5.0.0/24",
                "Gateway": "10.5.0.254"
            }]
        },
        "Internal": False,
        "Attachable": False,
        "Ingress": False,
        "ConfigFrom": {
            "Network": ""
        },
        "ConfigOnly": False,
        "Containers": {},
        "Options": {},
        "Labels": {}
    }]),
])
def test_parse_legacy_docker_network_inspect(indata, outdata):
    parsed = parse_legacy_docker_network_inspect(indata)  # type: ignore[name-defined] # pylint: disable=undefined-variable
    assert parsed == outdata, "expected: %r, got %r" % (outdata, parsed)
