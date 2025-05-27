#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, override

from cmk.ccc import version

from cmk.utils import paths
from cmk.utils.agent_registration import HostAgentConnectionMode

from cmk.gui.fields.utils import edition_field_description
from cmk.gui.i18n import _
from cmk.gui.permissions import PermissionSection, PermissionSectionRegistry

from cmk import fields


class _AgentConnectionField(fields.String):
    """A field representing the agent connection mode."""

    default_error_messages = {
        "edition_not_supported": "Agent connection field not supported in this edition.",
    }

    def __init__(self, **kwargs: Any):
        self._supported_editions = {version.Edition.CME, version.Edition.CCE}
        kwargs["description"] = edition_field_description(
            description=kwargs["description"],
            supported_editions=self._supported_editions,
        )
        super().__init__(**kwargs)

    @override
    def _validate(self, value: str) -> None:
        if version.edition(paths.omd_root) not in self._supported_editions:
            raise self.make_error("edition_not_supported")
        super()._validate(value)


CONNECTION_MODE_FIELD = _AgentConnectionField(
    enum=[HostAgentConnectionMode.PULL.value, HostAgentConnectionMode.PUSH.value],
    description=(
        "This configures the communication direction of this host.\n"
        f" * `{HostAgentConnectionMode.PULL.value}` (default) - The server will try to contact the monitored host and pull the data by initializing a TCP connection\n"
        f" * `{HostAgentConnectionMode.PUSH.value}` - the host is expected to send the data to the monitoring server without being triggered\n"
    ),
)


def register(permission_section_registry: PermissionSectionRegistry) -> None:
    permission_section_registry.register(PERMISSION_SECTION_AGENT_REGISTRATION)


PERMISSION_SECTION_AGENT_REGISTRATION = PermissionSection(
    name="agent_registration",
    title=_("Agent registration"),
)
