#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import sys
from io import StringIO

import pytest
from pytest import MonkeyPatch

from cmk.plugins.prometheus.special_agents.agent_prometheus import process_config_and_args


@pytest.mark.parametrize(
    "stdin_content, original_argv, expected_argv",
    [
        pytest.param(
            "{'connection': 'connection_to', 'protocol': 'http'}",
            ["--debug", "--cert-server-name", "example.com"],
            argparse.Namespace(
                debug=True,
                config="{'connection': 'connection_to', 'protocol': 'http'}",
                auth_method=None,
                disable_cert_verification=False,
                cert_server_name="example.com",
            ),
            id="basic config",
        ),
        pytest.param(
            "{'connection': 'localhost:9090', 'protocol': 'http'}",
            ["--cert-server-name", "prometheus_test", "auth_token", "--token", "token"],
            argparse.Namespace(
                debug=False,
                config="{'connection': 'localhost:9090', 'protocol': 'http'}",
                auth_method="auth_token",
                disable_cert_verification=False,
                cert_server_name="prometheus_test",
                token="token",
                token_reference=None,
            ),
            id="config with auth token (use of subparser)",
        ),
    ],
)
def test_process_config_and_args(
    monkeypatch: MonkeyPatch,
    stdin_content: str,
    original_argv: list[str],
    expected_argv: argparse.Namespace,
) -> None:
    monkeypatch.setattr(sys, "stdin", StringIO(stdin_content))
    processed_argv = process_config_and_args(original_argv)
    assert processed_argv == expected_argv


def test_process_config_and_args_config_missing(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", StringIO(""))

    with pytest.raises(SystemExit):
        # System exit 2, for missing --config argument
        process_config_and_args([])
