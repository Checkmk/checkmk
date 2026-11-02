#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.monitor.command import monitor_commands
from cmk.gui.monitor.services.table import SERVICE_SUPPORTED_ACTIONS


class _UserGrantedAll:
    def may(self, _permission_name: str) -> bool:
        return True


def test_every_service_command_the_shared_types_declare_is_registered_for_services() -> None:
    """A command renamed in its registry would otherwise silently drop out of the pages."""
    offered = monitor_commands.permitted_for(
        cast(LoggedInUser, _UserGrantedAll()), "service", SERVICE_SUPPORTED_ACTIONS
    )

    assert {command.ident for command in offered} == set(SERVICE_SUPPORTED_ACTIONS)
