#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import math
from typing import Annotated, Literal

from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.audit_log.models.response_models import (
    AuditLogEntryCollectionModel,
    AuditLogEntryExtensionsModel,
    AuditLogEntryModel,
)
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.watolib.audit_log import AuditLogFilterRaw, AuditLogStore, build_audit_log_filter
from cmk.web.utils import permission_verification as permissions

from ._family import AUDIT_LOG_FAMILY

# The 5 named values mirror ObjectRefType's members, plus the "All"/"None" sentinel filter
# values. Can't derive this from ObjectRefType at runtime: subclassing it is impossible (Python
# disallows extending an Enum that already has members), a `ObjectRefType | Literal[...]` union
# renders as an `anyOf` of two separate enums in the API docs instead of a single flat one, and
# mypy can't determine Enum() members from anything but a literal string/tuple/list/dict.
# test_audit_log.py::test_audit_log_object_type_filter_stays_in_sync_with_object_ref_type guards
# against drift if ObjectRefType ever changes.
AuditLogObjectType = Literal["All", "None", "Folder", "Host", "User", "Rule", "Ruleset"]


def list_audit_log_v1(
    date: Annotated[
        datetime.date,
        QueryParam(
            description=(
                "The date from which to obtain the audit log entries. The format has to "
                "conform to the ISO 8601 profile"
            ),
            example="2017-07-21",
        ),
    ],
    object_type: Annotated[
        AuditLogObjectType,
        QueryParam(
            description="The type of object we want to filter on",
            example="Folder",
        ),
    ] = "All",
    object_id: Annotated[
        str | None,
        QueryParam(
            description="Name of an object to filter by",
            example="host_01",
        ),
    ] = None,
    user_id: Annotated[
        str | None,
        QueryParam(
            description="An username to filter by",
            example="my_admin_user",
        ),
    ] = None,
    regexp: Annotated[
        str | None,
        QueryParam(
            description="A regular expression to be applied to the user_id, action and summary fields.",
            example="^l.*m.*p",
        ),
    ] = None,
) -> AuditLogEntryCollectionModel:
    """Get all audit log entries"""
    user.need_permission("wato.auditlog")

    timestamp_from, timestamp_to = _get_start_end_day_timestamp(date)

    ops: AuditLogFilterRaw = {
        "timestamp_from": timestamp_from,
        "timestamp_to": timestamp_to,
        "object_type": object_type,
        "object_ident": object_id,
        "user_id": user_id,
        "filter_regex": regexp,
    }

    entries = AuditLogStore().read(build_audit_log_filter(ops))

    return AuditLogEntryCollectionModel(
        value=[_create_entry(entry) for entry in entries],
    )


def _create_entry(entry: AuditLogStore.Entry) -> AuditLogEntryModel:
    return AuditLogEntryModel(
        title=str(entry.text),
        extensions=AuditLogEntryExtensionsModel(
            time=entry.time,
            user_id=entry.user_id,
            action=entry.action,
            details="" if entry.diff_text is None else entry.diff_text,
            object_type=None if entry.object_ref is None else entry.object_ref.ident,
            object_name=(None if entry.object_ref is None else entry.object_ref.object_type.name),
        ),
    )


def _get_start_end_day_timestamp(value: datetime.date) -> tuple[int, int]:
    start_of_day = datetime.datetime.combine(value, datetime.datetime.min.time())
    start_of_next_day = start_of_day + datetime.timedelta(days=1)

    return math.floor(start_of_day.timestamp()), math.floor(start_of_next_day.timestamp())


ENDPOINT_LIST_AUDIT_LOG = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("audit_log"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=permissions.Perm("wato.auditlog")),
    doc=EndpointDoc(family=AUDIT_LOG_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=list_audit_log_v1)},
)
