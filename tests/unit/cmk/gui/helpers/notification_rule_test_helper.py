#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.events.notify_types import EventRule, NotificationParameterID, NotificationRuleID


def mail_rule(
    description: str,
    *,
    parameter_id: str | None = "parameter_id",
    rule_id: str | None = None,
) -> EventRule:
    """A mail rule for the contacts of the notified object; no parameter cancels mails."""
    return EventRule(
        rule_id=NotificationRuleID(rule_id or description),
        allow_disable=False,
        contact_all=False,
        contact_all_with_email=False,
        contact_object=True,
        description=description,
        disabled=False,
        notify_plugin=(
            "mail",
            None if parameter_id is None else NotificationParameterID(parameter_id),
        ),
    )
