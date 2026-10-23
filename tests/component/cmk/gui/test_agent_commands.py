#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The community install commands, run in a shell against a fake curl and sudo."""

from typing import override

from cmk.ccc.hostaddress import HostName
from cmk.gui.agent_commands import build_agent_install_cmds
from cmk.shared_typing.agent_slideout import AgentInstallCmds
from tests.testlib.common.install_command import InstallCommandSuite


class TestCommunityInstallCommands(InstallCommandSuite):
    @override
    def install_cmds(self) -> AgentInstallCmds:
        return build_agent_install_cmds("2.5.0", HostName("my-host"))
