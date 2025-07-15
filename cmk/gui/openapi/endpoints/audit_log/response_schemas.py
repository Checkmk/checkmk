#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk import fields
from cmk.gui.fields.utils import BaseSchema


class AuditLogExtension(BaseSchema):
    time = fields.Integer(description="Timestamp of when the event occurred")
    user_id = fields.String(description="User id of whom provoked the event")
    action = fields.String(description="Action that was performed")
    summary = fields.String(description="Summary of the event")
    details = fields.String(description="Details of the event")
    object_type = fields.String(description="Object type associated to the event", allow_none=True)
    object_name = fields.String(description="Object name associated to the event", allow_none=True)


class AuditLogEntry(BaseSchema):
    title = fields.String(
        description="A human readable title of this object. Can be used for user interfaces.",
    )

    extensions = fields.Nested(
        AuditLogExtension,
        description="Data and Meta-Data of this audit log entry.",
    )


class AuditLogEntryCollection(BaseSchema):
    value = fields.List(
        fields.Nested(AuditLogEntry),
        description="A list of audit log objects.",
    )
