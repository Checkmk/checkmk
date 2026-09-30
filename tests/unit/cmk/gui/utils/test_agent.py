#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.utils.agent import raw_linux_agent_commands
from cmk.shared_typing.agent_slideout import UnbakedFallbackCommands


def test_raw_linux_agent_commands_keep_frontend_placeholders() -> None:
    assert raw_linux_agent_commands("2.5.0p1") == UnbakedFallbackCommands(
        linux_deb=(
            "wget {{SERVER}}/{{SITE}}/check_mk/agents/check-mk-agent_2.5.0p1-1_all.deb && \\\n"
            "sudo dpkg -i check-mk-agent_2.5.0p1-1_all.deb"
        ),
        linux_rpm=(
            "wget {{SERVER}}/{{SITE}}/check_mk/agents/check-mk-agent-2.5.0p1-1.noarch.rpm && \\\n"
            "sudo rpm -Uvh check-mk-agent-2.5.0p1-1.noarch.rpm"
        ),
    )
