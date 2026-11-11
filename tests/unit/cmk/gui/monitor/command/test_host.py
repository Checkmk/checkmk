#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.monitor.command import HOST_SUPPORTED_ACTIONS, monitor_commands


class _UserGrantedAll:
    def may(self, _permission_name: str) -> bool:
        return True


def test_every_host_command_the_shared_types_declare_is_registered_for_hosts() -> None:
    """A command renamed in its registry would otherwise silently drop out of the pages."""
    offered = monitor_commands.permitted_for(
        cast(LoggedInUser, _UserGrantedAll()), "host", HOST_SUPPORTED_ACTIONS
    )

    assert {command.ident for command in offered} == set(HOST_SUPPORTED_ACTIONS)
