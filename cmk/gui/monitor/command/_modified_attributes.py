#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Mapping


class ModifiableAttribute(enum.StrEnum):
    """What a command may switch off for a host or service until it is reset."""

    NOTIFICATIONS = "notifications"
    ACTIVE_CHECKS = "active_checks"
    PASSIVE_CHECKS = "passive_checks"


# As in the legacy commands, active and passive checks share one permission.
ATTRIBUTE_PERMISSIONS: Mapping[ModifiableAttribute, str] = {
    ModifiableAttribute.NOTIFICATIONS: "action.notifications",
    ModifiableAttribute.ACTIVE_CHECKS: "action.enablechecks",
    ModifiableAttribute.PASSIVE_CHECKS: "action.enablechecks",
}
