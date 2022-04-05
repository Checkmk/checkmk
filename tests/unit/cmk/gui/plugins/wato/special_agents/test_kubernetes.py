#!/usr/bin/env python3

# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.wato.special_agents.kubernetes import special_agents_kubernetes_transform


@pytest.mark.parametrize(
    "parameters, expected_result",
    [
        (
            {
                "url-prefix": "https://someserver:123/blah",
            },
            {
                "infos": ["nodes"],
                "no-cert-check": False,
                "namespaces": False,
                "api-server-endpoint": (
                    "url_custom",
                    "https://someserver:123/blah",
                ),
            },
        ),
        (
            {
                "url-prefix": "https://someserver",
                "port": 123,
                "path-prefix": "blah",
            },
            {
                "infos": ["nodes"],
                "no-cert-check": False,
                "namespaces": False,
                "api-server-endpoint": (
                    "url_custom",
                    "https://someserver:123/blah",
                ),
            },
        ),
        (
            {
                "port": 123,
                "path-prefix": "blah",
            },
            {
                "infos": ["nodes"],
                "no-cert-check": False,
                "namespaces": False,
                "api-server-endpoint": (
                    "ipaddress",
                    {
                        "port": 123,
                        "path-prefix": "blah",
                    },
                ),
            },
        ),
        (
            {},
            {
                "infos": ["nodes"],
                "no-cert-check": False,
                "namespaces": False,
                "api-server-endpoint": (
                    "ipaddress",
                    {},
                ),
            },
        ),
    ],
)
def test__special_agents_kubernetes_transform(parameters, expected_result):
    assert special_agents_kubernetes_transform(parameters) == expected_result
