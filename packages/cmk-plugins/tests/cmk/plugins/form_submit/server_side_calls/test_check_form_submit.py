#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.plugins.form_submit.server_side_calls.check_form_submit import (
    active_check_config as config,
)
from cmk.plugins.form_submit.server_side_calls.check_form_submit import UrlParams
from cmk.server_side_calls.v1 import HostConfig, IPv4Config

_TEST_HOST_CONFIG = HostConfig(
    name="hostname",
    ipv4_config=IPv4Config(address="test"),
)


@pytest.mark.parametrize(
    ["params", "host_config", "expected_args"],
    [
        pytest.param(
            {
                "name": "foo",
                "url_details": UrlParams(),
            },
            _TEST_HOST_CONFIG,
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
            _TEST_HOST_CONFIG,
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
            _TEST_HOST_CONFIG,
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
            _TEST_HOST_CONFIG,
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
            _TEST_HOST_CONFIG,
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
    commands = list(config(params, host_config))
    assert commands[0].command_arguments == expected_args
