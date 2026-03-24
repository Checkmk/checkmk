#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import MagicMock, patch

import pytest
from netapp_ontap import resources as NetAppResource
from netapp_ontap.error import NetAppRestError

from cmk.special_agents.agent_netapp_ontap import (
    agent_netapp_main,
    parse_arguments,
)
from cmk.special_agents.v0_unstable.agent_common import CannotRecover


class _AuthError(NetAppRestError):
    """NetAppRestError with status_code 401 for testing authentication failures."""

    def __init__(self) -> None:  # pylint: disable=super-init-not-called
        Exception.__init__(self, "401 Unauthorized")  # pylint: disable=non-parent-init-called

    @property
    def status_code(self) -> int:
        return 401


class _ServerError(NetAppRestError):
    """NetAppRestError with a non-auth status code for testing other API failures."""

    def __init__(self) -> None:  # pylint: disable=super-init-not-called
        Exception.__init__(self, "503 Service Unavailable")  # pylint: disable=non-parent-init-called

    @property
    def status_code(self) -> int:
        return 503


def test_agent_exits_1_when_connection_returns_401() -> None:
    """When the NetApp API returns a 401 auth error, agent_netapp_main should raise CannotRecover.

    Regression: after c6bf4fe, safe_write_section catches all exceptions including
    NetAppRestError(401), so the error never reaches the 401 handler in agent_netapp_main
    and the agent returns 0 instead of 1.
    """
    args = parse_arguments(
        [
            "--hostname",
            "myhost",
            "--username",
            "admin",
            "--password",
            "secret",
            "--no-cert-check",
            "--fetched-resources",
            "node",
        ]
    )

    with (
        patch("cmk.special_agents.agent_netapp_ontap.HostConnection") as mock_conn,
        patch.object(NetAppResource.Node, "get_collection", side_effect=_AuthError()),
        pytest.raises(CannotRecover, match="Authentication failed"),
    ):
        mock_conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        agent_netapp_main(args)


def test_agent_does_not_exit_1_when_connection_returns_non_auth_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A non-401 API error (e.g. 503) should not cause agent_netapp_main to return 1.
    The error is written as an error section and the agent exits cleanly with 0.
    """
    args = parse_arguments(
        [
            "--hostname",
            "myhost",
            "--username",
            "admin",
            "--password",
            "secret",
            "--no-cert-check",
            "--fetched-resources",
            "node",
        ]
    )

    with (
        patch("cmk.special_agents.agent_netapp_ontap.HostConnection") as mock_conn,
        patch.object(NetAppResource.Node, "get_collection", side_effect=_ServerError()),
    ):
        mock_conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)

        result = agent_netapp_main(args)

    assert result == 0
    assert "Authentication failed" not in capsys.readouterr().err
