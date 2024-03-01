#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest
from polyfactory.factories import DataclassFactory

from cmk.plugins.collection.server_side_calls.check_form_submit import active_check_config as config
from cmk.plugins.collection.server_side_calls.check_form_submit import UrlParams
from cmk.server_side_calls.v1 import (
    HostConfig,
    IPAddressFamily,
    NetworkAddressConfig,
    ResolvedIPAddressFamily,
)


class HostConfigFactory(DataclassFactory):
    __model__ = HostConfig


@pytest.mark.parametrize(
    ["params", "host_config", "expected_args"],
    [
        pytest.param(
            {
                "name": "foo",
                "url_details": UrlParams(),
            },
            HostConfigFactory.build(
                resolved_ipv4_address="test",
                resolved_ip_family=ResolvedIPAddressFamily.IPV4,
                address_config=NetworkAddressConfig(ip_family=IPAddressFamily.IPV4),
            ),
            [
                "test",
            ],
            id="minimal configuration",
        ),
        pytest.param(
            {
                "name": "foo",
                "url_details": UrlParams(port=80),
            },
            HostConfigFactory.build(
                resolved_ipv4_address="test",
                resolved_ip_family=ResolvedIPAddressFamily.IPV4,
                address_config=NetworkAddressConfig(ip_family=IPAddressFamily.IPV4),
            ),
            [
                "test",
                "--port",
                "80",
            ],
            id="with port",
        ),
        pytest.param(
            {
                "name": "foo",
                "url_details": UrlParams(
                    hosts=["12.3.4.51", "some-other-host"],
                    uri="/some/where",
                    tls_configuration="tls_standard",
                    timeout=5,
                    expect_regex=".*abc",
                    form_name="cool form",
                    query="key1=val1&key2=val2",
                    num_succeeded=(1, 0),
                ),
            },
            HostConfigFactory.build(
                resolved_ipv4_address="hurz",
                resolved_ip_family=ResolvedIPAddressFamily.IPV4,
            ),
            [
                "12.3.4.51",
                "some-other-host",
                "--uri",
                "/some/where",
                "--tls_configuration",
                "tls_standard",
                "--timeout",
                "5",
                "--expected_regex",
                ".*abc",
                "--form_name",
                "cool form",
                "--query_params",
                "key1=val1&key2=val2",
                "--levels",
                "1",
                "0",
            ],
            id="extensive configuration",
        ),
        pytest.param(
            {
                "name": "foo",
                "url_details": UrlParams(
                    hosts=["some-other-host"],
                    tls_configuration="no_tls",
                ),
            },
            HostConfigFactory.build(
                resolved_ipv4_address="hurz",
                resolved_ip_family=ResolvedIPAddressFamily.IPV4,
            ),
            [
                "some-other-host",
                "--tls_configuration",
                "no_tls",
            ],
            id="tls disabled",
        ),
        pytest.param(
            {
                "name": "foo",
                "url_details": UrlParams(
                    hosts=["some-other-host"],
                    tls_configuration="tls_no_cert_valid",
                ),
            },
            HostConfigFactory.build(
                resolved_ipv4_address="hurz",
                resolved_ip_family=ResolvedIPAddressFamily.IPV4,
            ),
            [
                "some-other-host",
                "--tls_configuration",
                "tls_no_cert_valid",
            ],
            id="server certificate validation disabled",
        ),
    ],
)
def test_check_form_submit_argument_parsing(
    params: dict[str, str | UrlParams],
    host_config: HostConfig,
    expected_args: Sequence[object],
) -> None:
    """Tests if all required arguments are present."""
    commands = list(config(params, host_config, {}))
    assert commands[0].command_arguments == expected_args
