#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

import pytest

from cmk.gui.plugins.wato import active_checks_module


@pytest.mark.parametrize(
    ["deprecated_params", "transformed_params"],
    [
        pytest.param(
            (
                "name",
                {
                    "ssl": True,
                    "expect_regex": ".*some_form.*",
                    "num_succeeded": (
                        3,
                        2,
                    ),
                },
            ),
            (
                "name",
                {
                    "tls_configuration": "tls_standard",
                    "expect_regex": ".*some_form.*",
                    "num_succeeded": (
                        3,
                        2,
                    ),
                },
            ),
            id="old format",
        ),
        pytest.param(
            (
                "name",
                {
                    "tls_configuration": "no_tls",
                    "timeout": 13,
                },
            ),
            (
                "name",
                {
                    "tls_configuration": "no_tls",
                    "timeout": 13,
                },
            ),
            id="current format without tls",
        ),
        pytest.param(
            (
                "name",
                {
                    "tls_configuration": "tls_standard",
                },
            ),
            (
                "name",
                {
                    "tls_configuration": "tls_standard",
                },
            ),
            id="current format with standard tls",
        ),
        pytest.param(
            (
                "name",
                {
                    "tls_configuration": "tls_no_cert_valid",
                },
            ),
            (
                "name",
                {
                    "tls_configuration": "tls_no_cert_valid",
                },
            ),
            id="current format with tls, server certificate validation disabled",
        ),
    ],
)
def test_transform_form_submit(
    deprecated_params: tuple[str, Mapping[str, object]],
    transformed_params: tuple[str, Mapping[str, object]],
) -> None:
    assert active_checks_module._transform_form_submit(deprecated_params) == transformed_params
