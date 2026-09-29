#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPStatus

from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.watolib import groups
from cmk.gui.watolib.groups import GroupInUseException, UnknownGroupException
from cmk.gui.watolib.hosts_and_folders import make_folder_tree

from ._family import HOST_GROUP_FAMILY
from ._utils import make_pending_changes, RW_PERMISSIONS
from .models.request_models import BulkDeleteHostGroup


def bulk_delete_host_group_v1(api_context: ApiContext, body: BulkDeleteHostGroup) -> None:
    """Bulk delete host groups"""
    api_context.user.need_permission("wato.edit")
    api_context.user.need_permission("wato.groups")
    tree = make_folder_tree(api_context.config)
    for group_name in body.entries:
        try:
            groups.delete_group(
                group_name,
                "host",
                tree=tree,
                pprint_value=api_context.config.wato_pprint_config,
                pending_changes=make_pending_changes(api_context),
            )
        except GroupInUseException as exc:
            raise ProblemException(
                status=HTTPStatus.CONFLICT,
                title="Group in use problem",
                detail=str(exc),
            ) from exc
        except UnknownGroupException as exc:
            raise ProblemException(
                status=HTTPStatus.NOT_FOUND,
                title="Unknown group problem",
                detail=str(exc),
            ) from exc


ENDPOINT_BULK_DELETE_HOST_GROUP = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("host_group_config", "bulk-delete"),
        link_relation="cmk/bulk_delete",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=HOST_GROUP_FAMILY.name),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=bulk_delete_host_group_v1,
            additional_status_codes=[HTTPStatus.NOT_FOUND, HTTPStatus.CONFLICT],
        )
    },
)
