#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.utils.agent_registration import HostAgentConnectionMode

from cmk.gui.i18n import _
from cmk.gui.permissions import PermissionSection, PermissionSectionRegistry

from cmk import fields

CONNECTION_MODE_FIELD = fields.String(
    enum=[HostAgentConnectionMode.PULL.value, HostAgentConnectionMode.PUSH.value],
    description=(
        "This configures the communication direction of this host.\n"
        f" * `{HostAgentConnectionMode.PULL.value}` (default) - The server will try to contact the monitored host and pull the data by initializing a TCP connection\n"
        f" * `{HostAgentConnectionMode.PUSH.value}` - the host is expected to send the data to the monitoring server without being triggered\n"
    ),
)


def register(permission_section_registry: PermissionSectionRegistry) -> None:
    permission_section_registry.register(PermissionSectionAgentRegistration())


class PermissionSectionAgentRegistration(PermissionSection):
    @override
    @property
    def name(self) -> str:
        return "agent_registration"

    @override
    @property
    def title(self) -> str:
        return _("Agent registration")
