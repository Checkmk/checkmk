#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPStatus
from typing import Annotated

from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.watolib import groups
from cmk.gui.watolib.groups import GroupInUseException, UnknownGroupException
from cmk.gui.watolib.hosts_and_folders import make_folder_tree

from ._family import HOST_GROUP_FAMILY
from ._utils import make_pending_changes, RW_PERMISSIONS


def delete_host_group_v1(
    api_context: ApiContext,
    name: Annotated[
        str,
        PathParam(description="The identifier name of the group.", example="pathname"),
    ],
) -> None:
    """Delete a host group"""
    api_context.user.need_permission("wato.edit")
    api_context.user.need_permission("wato.groups")
    try:
        groups.delete_group(
            name,
            "host",
            tree=make_folder_tree(api_context.config),
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


ENDPOINT_DELETE_HOST_GROUP = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("host_group_config", "{name}"),
        link_relation=".../delete",
        method="delete",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=HOST_GROUP_FAMILY.name),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=delete_host_group_v1,
            additional_status_codes=[HTTPStatus.CONFLICT],
        )
    },
)
