#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest

from cmk.plugins.jolokia.special_agent import agent_jolokia


def test_parse_no_arguments() -> None:
    args = agent_jolokia.parse_arguments([])

    assert args.client_cert is None
    assert args.client_key is None
    assert args.password is None
    assert args.port == 8080
    assert args.product is None
    assert args.protocol == "http"
    assert args.server == "localhost"
    assert args.suburi == "jolokia"
    assert args.timeout == 1.0


@pytest.mark.parametrize(
    ["passed_args", "expected_product"],
    [
        pytest.param(
            [
                "--client_cert",
                "client_cert",
                "--client_key",
                "client_key",
                "--debug",
            ],
            None,
            id="default product",
        ),
        pytest.param(
            [
                "--client_cert",
                "client_cert",
                "--client_key",
                "client_key",
                "--debug",
                "--product",
                "tomcat",
            ],
            "tomcat",
            id="specific product",
        ),
    ],
)
def test_parse_arguments_product(passed_args: Sequence[str], expected_product: str) -> None:
    args = agent_jolokia.parse_arguments(passed_args)

    assert args.client_cert == "client_cert"
    assert args.client_key == "client_key"
    assert args.debug is True
    assert args.mode == "digest"
    assert args.port == 8080
    assert args.product is expected_product
