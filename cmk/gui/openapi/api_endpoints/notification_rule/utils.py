#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.ccc.site import omd_site
from cmk.events.notify_types import EventRule, NotificationRuleID
from cmk.gui.i18n import _
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.pending_changes import (
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)

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


def make_pending_changes(api_context: ApiContext) -> PendingChanges:
    return PendingChanges(
        activation_sites=activation_sites(api_context.config.sites),
        local_site=omd_site(),
        acting_user=api_context.user.id,
        store=PendingChangesStore(),
        hooks=(
            make_audit_log_change_hook(use_git=api_context.config.wato_use_git),
            index_update_change_hook,
        ),
    )
