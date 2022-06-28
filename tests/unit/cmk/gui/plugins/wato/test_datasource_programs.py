#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.wato.datasource_programs import (
    _special_agents_innovaphone_transform,
    _special_agents_kubernetes_transform,
    _transform_agent_prometheus,
    MultisiteBiDatasource,
)


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
    assert _special_agents_kubernetes_transform(parameters) == expected_result


@pytest.mark.parametrize(
    "parameters, expected_result",
    [
        (
            ("USER123", "PasswordABC"),
            {
                "auth_basic": {"password": ("password", "PasswordABC"), "username": "USER123"},
            },
        ),
    ],
)
def test__special_agents_innovaphone_transform(parameters, expected_result):
    assert _special_agents_innovaphone_transform(parameters) == expected_result


@pytest.fixture(scope="function")
def _bi_datasource_parameters():
    # parameter format introduced with 2.0.0p9
    return {
        "site": "local",
        "credentials": "automation",
        "filter": {"aggr_name": ["Host admin-pc"], "aggr_group_prefix": ["Hosts"]},
    }


@pytest.mark.parametrize(
    "value",
    [
        (
            # filter keys till 2.0.0p8
            {
                "site": "local",
                "credentials": "automation",
                "filter": {"aggr_name_regex": ["Host admin-pc"], "aggr_groups": ["Hosts"]},
            }
        ),
        (
            {
                # filter keys from 2.0.0p9
                "site": "local",
                "credentials": "automation",
                "filter": {"aggr_name": ["Host admin-pc"], "aggr_group_prefix": ["Hosts"]},
            }
        ),
    ],
)
def test_bi_datasource_parameters(value, _bi_datasource_parameters):
    assert (
        MultisiteBiDatasource().get_valuespec().transform_value(value) == _bi_datasource_parameters
    )


@pytest.mark.parametrize(
    "parameters, expected_result",
    [
        (
            {},
            {
                "verify-cert": False,
            },
        ),
        (
            {
                "connection": "host_name",
                "port": 9090,
            },
            {
                "connection": ("host_name", {"port": 9090}),
                "verify-cert": False,
            },
        ),
        (
            {
                "connection": ("url_custom", {"url_address": "custom_url"}),
                "port": 9090,
            },
            {
                "connection": ("url_custom", {"url_address": "custom_url"}),
                "verify-cert": False,
            },
        ),
        (
            {
                "connection": "ip_address",
                "port": 9090,
                "auth_basic": {"username": "asdasd", "password": ("password", "asd")},
            },
            {
                "connection": ("ip_address", {"port": 9090}),
                "verify-cert": False,
                "auth_basic": (
                    "auth_login",
                    {"username": "asdasd", "password": ("password", "asd")},
                ),
            },
        ),
        (
            {
                "connection": ("ip_address", {"port": 9090}),
                "verify-cert": True,
                "auth_basic": (
                    "auth_login",
                    {"username": "asdasd", "password": ("password", "asd")},
                ),
            },
            {
                "connection": ("ip_address", {"port": 9090}),
                "verify-cert": True,
                "auth_basic": (
                    "auth_login",
                    {"username": "asdasd", "password": ("password", "asd")},
                ),
            },
        ),
    ],
)
def test__transform_agent_prometheus(parameters, expected_result) -> None:
    assert _transform_agent_prometheus(parameters) == expected_result
