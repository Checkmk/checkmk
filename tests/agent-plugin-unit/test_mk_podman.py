#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from agents.plugins.mk_podman import get_piggyback_host, get_socket_owner, PiggybackNameMethod


def test_get_socket_owner_returns_username() -> None:
    stat_result = MagicMock()
    stat_result.st_uid = 1001
    with patch("os.stat", return_value=stat_result):
        with patch("pwd.getpwuid", return_value=MagicMock(pw_name="testuser")):
            assert get_socket_owner(Path("/run/user/1001/podman/podman.sock")) == "testuser"


def test_get_socket_owner_returns_none_on_oserror() -> None:
    with patch("os.stat", side_effect=OSError("no such file")):
        assert get_socket_owner(Path("/nonexistent/podman.sock")) is None


def test_get_socket_owner_returns_none_on_keyerror() -> None:
    stat_result = MagicMock()
    stat_result.st_uid = 9999
    with patch("os.stat", return_value=stat_result):
        with patch("pwd.getpwuid", side_effect=KeyError(9999)):
            assert get_socket_owner(Path("/run/podman/podman.sock")) is None


@pytest.mark.parametrize(
    "container_id, container_name, piggyback_name_method, nodename, expected",
    [
        pytest.param(
            "",
            "mycontainer",
            PiggybackNameMethod.NAME,
            None,
            None,
            id="empty container_id returns None for NAME",
        ),
        pytest.param(
            "",
            "mycontainer",
            PiggybackNameMethod.NAME_ID,
            None,
            None,
            id="empty container_id returns None for NAME_ID",
        ),
        pytest.param(
            "",
            "mycontainer",
            PiggybackNameMethod.NODENAME_NAME,
            None,
            None,
            id="empty container_id returns None for NODENAME_NAME",
        ),
        pytest.param(
            "abc123",
            "mycontainer",
            PiggybackNameMethod.NAME,
            None,
            "mycontainer",
            id="NAME method returns container name as-is",
        ),
        pytest.param(
            "abc123def456789",
            "mycontainer",
            PiggybackNameMethod.NAME_ID,
            None,
            "mycontainer_abc123def456",
            id="NAME_ID method returns name_<first 12 chars of id>",
        ),
        pytest.param(
            "abcdefghijklmnop",
            "mycontainer",
            PiggybackNameMethod.NAME_ID,
            None,
            "mycontainer_abcdefghijkl",
            id="NAME_ID truncates id to 12 chars",
        ),
        pytest.param(
            "abc123",
            "mycontainer",
            PiggybackNameMethod.NODENAME_NAME,
            "mynode",
            "mynode_mycontainer",
            id="NODENAME_NAME with explicit nodename uses provided nodename",
        ),
        pytest.param(
            "abc123",
            "mycontainer",
            PiggybackNameMethod.NODENAME_NAME,
            None,
            "fakehost_mycontainer",
            id="NODENAME_NAME with nodename=None falls back to os.uname()[1]",
        ),
    ],
)
def test_get_piggyback_host(
    container_id: str,
    container_name: str,
    piggyback_name_method: PiggybackNameMethod,
    nodename: Optional[str],
    expected: Optional[str],
) -> None:
    with patch("os.uname", return_value=("", "fakehost", "", "", "")):
        result = get_piggyback_host(container_id, container_name, piggyback_name_method, nodename)
    assert result == expected
