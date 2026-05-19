#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui import sites
from cmk.gui.livestatus_utils.commands.lowlevel import send_command
from cmk.gui.session_context import SuperUserContext
from cmk.livestatus_client.testing import MockLiveStatusConnection


@pytest.mark.usefixtures("request_context")
def test_send_command_empty_params(mock_livestatus: MockLiveStatusConnection) -> None:
    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        live.expect_query(
            "COMMAND [...] ADD_HOST_COMMENT",
            match_type="ellipsis",
        )
        send_command(sites.live(), "ADD_HOST_COMMENT", [])


@pytest.mark.usefixtures("request_context")
def test_send_command_int_params(mock_livestatus: MockLiveStatusConnection) -> None:
    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        live.expect_query(
            "COMMAND [...] ADD_HOST_COMMENT;1;2;3",
            match_type="ellipsis",
        )
        send_command(sites.live(), "ADD_HOST_COMMENT", [1, 2, 3])


@pytest.mark.usefixtures("request_context")
def test_send_command_invalid_param_type(mock_livestatus: MockLiveStatusConnection) -> None:
    with mock_livestatus(expect_status_query=True), SuperUserContext():
        with pytest.raises(ValueError, match="Unknown type of parameter 0"):
            send_command(sites.live(), "ADD_HOST_COMMENT", [object()])
