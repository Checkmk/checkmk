#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.gui.i18n import _
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.utils import permission_verification as permissions
from cmk.utils.notify_types import EventRule, NotificationRuleID

RO_PERMISSIONS = permissions.Perm("general.edit_notifications")
RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.see_all_folders"),
        RO_PERMISSIONS,
    ]
)


def index_of_notification_rule(rules: Sequence[EventRule], rule_id: NotificationRuleID) -> int:
    for index, rule in enumerate(rules):
        if rule["rule_id"] == rule_id:
            return index
    raise ProblemException(
        status=404,
        title=_("The requested notification rule was not found"),
        detail=_("The rule_id %(rule_id)s does not exist.") % {"rule_id": rule_id},
    )
