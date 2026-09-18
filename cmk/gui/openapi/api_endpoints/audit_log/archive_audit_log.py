#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.watolib.audit_log import AuditLogStore
from cmk.web.utils import permission_verification as permissions

from ._family import AUDIT_LOG_FAMILY

ARCHIVE_PERMISSION = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.auditlog"),
        permissions.Perm("wato.clear_auditlog"),
    ]
)


def archive_audit_log_v1() -> ApiResponse[None]:
    """Move audit log entries to archive"""
    user.need_permission("wato.edit")
    user.need_permission("wato.auditlog")
    user.need_permission("wato.clear_auditlog")
    AuditLogStore().clear()
    return ApiResponse(body=None, status_code=204)


ENDPOINT_ARCHIVE_AUDIT_LOG = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("audit_log", "archive"),
        link_relation=".../action",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=ARCHIVE_PERMISSION),
    doc=EndpointDoc(family=AUDIT_LOG_FAMILY.name),
    behavior=EndpointBehavior(update_config_generation=False),
    versions={APIVersion.V1: EndpointHandler(handler=archive_audit_log_v1)},
)
