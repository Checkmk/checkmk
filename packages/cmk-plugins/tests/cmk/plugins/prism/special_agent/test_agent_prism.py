# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tests for agent_prism connection error handling.

Regression tests for crash group 3603: RemoteDisconnected was not caught
because the old urllib-based request helper let it propagate.  The agent was
rewritten to use the requests library; requests wraps RemoteDisconnected inside
requests.exceptions.ConnectionError, which agent_prism_main now catches
explicitly and returns exit code 1 instead of crashing.
"""

import argparse
from unittest.mock import patch

import pytest
import requests

from cmk.plugins.prism.special_agent.agent_prism import agent_prism_main, parse_arguments


def _make_args(**kwargs: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "server": "prism.example.com",
        "port": 9440,
        "username": "admin",
        "password": "secret",
        "timeout": 10,
        "no_cert_check": True,
        "cert_server_name": None,
        "debug": False,
        "verbose": 0,
        "vcrtrace": False,
        "api_version": "legacy",
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _patched_resolve(ns: argparse.Namespace, key: str) -> object:
    """Minimal stand-in for resolve_secret_option that returns an object with .reveal()."""

    class _Revealed:
        def reveal(self) -> str:
            return str(getattr(ns, key))

    return _Revealed()


@pytest.mark.parametrize(
    "connection_error",
    [
        requests.exceptions.ConnectionError("Remote end closed connection without response"),
        requests.exceptions.ReadTimeout("timed out"),
    ],
    ids=["ConnectionError", "ReadTimeout"],
)
def test_agent_prism_main_handles_connection_errors_gracefully(
    connection_error: Exception,
) -> None:
    """agent_prism_main must return 1 (not crash) when the Prism gateway is unreachable.

    Before the fix the agent used urllib which raised RemoteDisconnected directly.
    After the fix requests wraps it as ConnectionError, which is caught in
    agent_prism_main's except clause.
    """
    args = _make_args()
    with (
        patch(
            "cmk.plugins.prism.special_agent.agent_prism.fetch_from_gateway",
            side_effect=connection_error,
        ),
        patch(
            "cmk.plugins.prism.special_agent.agent_prism.resolve_secret_option",
            side_effect=_patched_resolve,
        ),
    ):
        result = agent_prism_main(args)

    assert result == 1


def test_parse_arguments_defaults_to_legacy_api() -> None:
    args = parse_arguments(["--server", "prism", "--username", "admin", "--password", "pw"])
    assert args.api_version == "legacy"
