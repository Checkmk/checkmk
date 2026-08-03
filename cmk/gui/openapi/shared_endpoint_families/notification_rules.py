#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

NOTIFICATION_RULES_FAMILY = EndpointFamily(
    name="Notification Rules",
    description=(
        """

The notification rules endpoints give you the flexibility to create, edit, delete, move and show
all notification rules configured.

* POST for creating new notification rules.
* PUT for updating current notification rules.
* LIST for listing all current notification rules.
* GET for getting a single notification rule.
* DELETE for deleting a single notification rule.
* MOVE for changing the position of a notification rule within the rule chain.

Notification rules are evaluated from top to bottom, so their position matters. The current
position of a rule is exposed as the `rule_index` extension of every notification rule object.

"""
    ),
    doc_group="Setup",
)
