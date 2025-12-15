#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.permissions import PermissionSection, PermissionSectionRegistry


def register(permission_section_registry: PermissionSectionRegistry) -> None:
    permission_section_registry.register(PERMISSION_SECTION_AGENT_REGISTRATION)


PERMISSION_SECTION_AGENT_REGISTRATION = PermissionSection(
    name="agent_registration",
    title=_("Agent registration"),
)
