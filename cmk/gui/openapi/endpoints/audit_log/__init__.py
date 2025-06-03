#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Audit logs

The audit log records the activities taking place in CheckMK. These endpoints allow you to read and clean these logs

"""

import datetime
import math
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.audit_log.request_schemas import (
    date_field,
    object_name_field,
    object_type_field,
    regexp_field,
    user_id_field,
)
from cmk.gui.openapi.endpoints.audit_log.response_schemas import AuditLogEntryCollection
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import serve_json
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.audit_log import AuditLogFilterRaw, AuditLogStore, build_audit_log_filter

AuditLogResponse = dict[str, Any]

CLEAR_PERMISSION = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.auditlog"),
        permissions.Perm("wato.clear_auditlog"),
    ]
)

LIST_PERMISSION = permissions.Perm("wato.auditlog")


@Endpoint(
    constructors.domain_type_action_href("audit_log", "archive"),
    ".../action",
    method="post",
    output_empty=True,
    permissions_required=CLEAR_PERMISSION,
    update_config_generation=False,
)
def archive_logs(params: Mapping[str, Any]) -> Response:
    """Move audit log entries to archive"""
    user.need_permission("wato.edit")
    user.need_permission("wato.auditlog")
    user.need_permission("wato.clear_auditlog")
    AuditLogStore().clear()
    return Response(status=204)


@Endpoint(
    constructors.collection_href("audit_log"),
    ".../collection",
    method="get",
    response_schema=AuditLogEntryCollection,
    permissions_required=LIST_PERMISSION,
    query_params=[
        {"object_type": object_type_field},
        {"object_id": object_name_field},
        {"user_id": user_id_field},
        {"date": date_field},
        {"regexp": regexp_field},
    ],
)
def get_all(params: Mapping[str, Any]) -> Response:
    """Get all audit log entries"""
    user.need_permission("wato.auditlog")

    timestamp_from, timestamp_to = _get_start_end_day_timestamp(params["date"])

    ops: AuditLogFilterRaw = {
        "timestamp_from": timestamp_from,
        "timestamp_to": timestamp_to,
        "object_type": params.get("object_type"),
        "object_ident": params.get("object_ident"),
        "user_id": params.get("user_id"),
        "filter_regex": params.get("filter_regex"),
    }

    entries = AuditLogStore().read(build_audit_log_filter(ops))

    return serve_json(data=_create_collection(entries))


def _create_collection(collection: Sequence[AuditLogStore.Entry]) -> AuditLogResponse:
    new_collection: AuditLogResponse = {
        "value": [_create_entry(entry) for entry in collection],
    }

    return new_collection


def _create_entry(entry: AuditLogStore.Entry) -> AuditLogResponse:
    result: AuditLogResponse = {
        "title": str(entry.text),
        "extensions": {
            "time": entry.time,
            "user_id": entry.user_id,
            "action": entry.action,
            "details": "" if entry.diff_text is None else entry.diff_text,
            "object_type": None if entry.object_ref is None else entry.object_ref.ident,
            "object_name": None if entry.object_ref is None else entry.object_ref.object_type.name,
        },
    }

    return result


def _get_start_end_day_timestamp(value: datetime.date) -> tuple[int, int]:
    start_of_day = datetime.datetime.combine(value, datetime.datetime.min.time())
    start_of_next_day = start_of_day + datetime.timedelta(days=1)

    return math.floor(start_of_day.timestamp()), math.floor(start_of_next_day.timestamp())


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(get_all, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(archive_logs, ignore_duplicates=ignore_duplicates)
