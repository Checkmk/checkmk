#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import itertools
from typing import Annotated

from annotated_types import MinLen

from cmk.ccc.hostaddress import HostName
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.watolib.check_mk_automations import delete_hosts
from cmk.gui.watolib.hosts_and_folders import make_folder_tree

from ._family import HOST_CONFIG_FAMILY
from ._utils import make_pending_changes, PERMISSIONS_DELETE


@api_model
class BulkDeleteHostModel:
    entries: Annotated[
        list[Annotated[HostName, TypedPlainValidator(str, HostConverter().host_name)]],
        MinLen(1),
    ] = api_field(
        description="A list of host names.",
        example=["example.com", "host2.example.com"],
    )


def bulk_delete_host_v1(
    api_context: ApiContext,
    body: BulkDeleteHostModel,
) -> ApiResponse[None]:
    """Bulk delete hosts"""
    api_context.user.need_permission("wato.edit")
    hostnames = body.entries

    # Ideally, we would not need folder id's. However, folders cannot be sorted.
    folder_by_id = {}
    folder_id_by_hostname = {}
    tree = make_folder_tree(api_context.config)
    for hostname in hostnames:
        folder = tree.load_host(hostname).folder()
        folder_id_by_hostname[hostname] = folder.id()
        folder_by_id[folder.id()] = folder

    for id_, hostnames_per_folder in itertools.groupby(
        sorted(hostnames, key=folder_id_by_hostname.__getitem__),
        key=folder_id_by_hostname.__getitem__,
    ):
        folder = folder_by_id[id_]
        # Calling Folder.delete_hosts is very expensive. Thus, we only call it once per folder.
        folder.delete_hosts(
            list(hostnames_per_folder),
            automation=delete_hosts,
            pprint_value=api_context.config.wato_pprint_config,
            debug=api_context.config.debug,
            pending_changes=make_pending_changes(api_context),
            acting_user=api_context.user,
        )

    return ApiResponse(body=None, status_code=204)


ENDPOINT_BULK_DELETE_HOST = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("host_config", "bulk-delete"),
        link_relation="cmk/bulk_delete",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_DELETE),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=bulk_delete_host_v1)},
)
