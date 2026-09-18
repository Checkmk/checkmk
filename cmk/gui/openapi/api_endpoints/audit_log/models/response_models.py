#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted


@api_model
class AuditLogEntryExtensionsModel:
    time: int = api_field(description="Timestamp of when the event occurred", example=1690000000)
    user_id: str = api_field(description="User id of whom provoked the event", example="cmkadmin")
    action: str = api_field(description="Action that was performed", example="edit-host")
    # never populated, kept for backwards compatibility with the legacy endpoint
    summary: str | ApiOmitted = api_field(
        description="Summary of the event",
        example="Host edited",
        default_factory=ApiOmitted,
    )
    details: str = api_field(description="Details of the event", example="Changed IP address")
    object_type: str | None = api_field(
        description="Object type associated to the event", example="Host"
    )
    object_name: str | None = api_field(
        description="Object name associated to the event", example="host_01"
    )


@api_model
class AuditLogEntryModel:
    title: str = api_field(
        description="A human readable title of this object. Can be used for user interfaces.",
        example="Host edited",
    )
    extensions: AuditLogEntryExtensionsModel = api_field(
        description="Data and Meta-Data of this audit log entry."
    )


@api_model
class AuditLogEntryCollectionModel:
    value: list[AuditLogEntryModel] = api_field(
        description="A list of audit log objects.", example=[]
    )
