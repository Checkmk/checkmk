#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Host groups

Host groups are a way to organize hosts in Checkmk for monitoring.
By using a host group you can generate suitable views for overview and/or analysis.

The hosts part of a host group can be queried using the Monitoring's relevant host_status endpoints.

You can find an introduction to hosts including host groups in the
[Checkmk guide](https://docs.checkmk.com/latest/en/wato_hosts.html).

A host group object can have the following relations present in `links`:

 * `self` - The host group itself.
 * `urn:org.restfulobject/rels:update` - An endpoint to change this host group.
 * `urn:org.restfulobject/rels:delete` - An endpoint to delete this host group.

"""

from collections.abc import Mapping
from typing import Any

from cmk.ccc import version

from cmk.utils import paths

from cmk.gui.config import active_config
from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.host_group_config.request_schemas import (
    BulkDeleteHostGroup,
    BulkInputHostGroup,
    BulkUpdateHostGroup,
    InputHostGroup,
    UpdateHostGroupAttributes,
)
from cmk.gui.openapi.endpoints.host_group_config.response_schemas import (
    HostGroup,
    HostGroupCollection,
)
from cmk.gui.openapi.endpoints.utils import (
    build_group_list,
    fetch_group,
    fetch_specific_groups,
    prepare_groups,
    serialize_group,
    serialize_group_list,
    serve_group,
    update_customer_info,
    update_groups,
    updated_group_details,
)
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.parameters import GROUP_NAME_FIELD
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import ProblemException, serve_json
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib import groups
from cmk.gui.watolib.groups import GroupInUseException, UnknownGroupException
from cmk.gui.watolib.groups_io import load_host_group_information

PERMISSIONS = permissions.Perm("wato.groups")

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        PERMISSIONS,
    ]
)


@Endpoint(
    constructors.collection_href("host_group_config"),
    "cmk/create",
    method="post",
    etag="output",
    request_schema=InputHostGroup,
    response_schema=HostGroup,
    permissions_required=RW_PERMISSIONS,
)
def create(params: Mapping[str, Any]) -> Response:
    """Create a host group"""
    user.need_permission("wato.edit")
    user.need_permission("wato.groups")
    body = params["body"]
    name = body["name"]
    group_details = {"alias": body["alias"]}
    if version.edition(paths.omd_root) is version.Edition.CME:
        group_details = update_customer_info(group_details, body["customer"])
    groups.add_group(name, "host", group_details, pprint_value=active_config.wato_pprint_config)
    group = fetch_group(name, "host")
    return serve_group(group, serialize_group("host_group_config"))


@Endpoint(
    constructors.domain_type_action_href("host_group_config", "bulk-create"),
    "cmk/bulk_create",
    method="post",
    request_schema=BulkInputHostGroup,
    response_schema=HostGroupCollection,
    permissions_required=RW_PERMISSIONS,
)
def bulk_create(params: Mapping[str, Any]) -> Response:
    """Bulk create host groups"""
    user.need_permission("wato.edit")
    user.need_permission("wato.groups")
    body = params["body"]
    entries = body["entries"]
    host_group_details = prepare_groups("host", entries)

    host_group_names = []
    for group_name, group_details in host_group_details.items():
        groups.add_group(
            group_name, "host", group_details, pprint_value=active_config.wato_pprint_config
        )
        host_group_names.append(group_name)

    host_groups = fetch_specific_groups(host_group_names, "host")
    return serve_json(serialize_group_list("host_group_config", host_groups))


@Endpoint(
    constructors.collection_href("host_group_config"),
    ".../collection",
    method="get",
    response_schema=HostGroupCollection,
    permissions_required=PERMISSIONS,
)
def list_groups(params: Mapping[str, Any]) -> Response:
    """Show all host groups"""
    user.need_permission("wato.groups")
    collection = build_group_list(load_host_group_information())
    return serve_json(serialize_group_list("host_group_config", collection))


@Endpoint(
    constructors.object_href("host_group_config", "{name}"),
    ".../delete",
    method="delete",
    path_params=[GROUP_NAME_FIELD],
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
    additional_status_codes=[409],
)
def delete(params: Mapping[str, Any]) -> Response:
    """Delete a host group"""
    user.need_permission("wato.edit")
    user.need_permission("wato.groups")
    name = params["name"]
    try:
        groups.delete_group(name, "host", pprint_value=active_config.wato_pprint_config)
    except GroupInUseException as exc:
        raise ProblemException(
            status=409,
            title="Group in use problem",
            detail=str(exc),
        )
    except UnknownGroupException as exc:
        raise ProblemException(
            status=404,
            title="Unknown group problem",
            detail=str(exc),
        )

    return Response(status=204)


@Endpoint(
    constructors.domain_type_action_href("host_group_config", "bulk-delete"),
    ".../delete",
    method="post",
    request_schema=BulkDeleteHostGroup,
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
    additional_status_codes=[404, 409],
)
def bulk_delete(params: Mapping[str, Any]) -> Response:
    """Bulk delete host groups"""
    user.need_permission("wato.edit")
    user.need_permission("wato.groups")
    body = params["body"]
    for group_name in body["entries"]:
        try:
            groups.delete_group(group_name, "host", pprint_value=active_config.wato_pprint_config)
        except GroupInUseException as exc:
            raise ProblemException(
                status=409,
                title="Group in use problem",
                detail=str(exc),
            )
        except UnknownGroupException as exc:
            raise ProblemException(
                status=404,
                title="Unknown group problem",
                detail=str(exc),
            )
    return Response(status=204)


@Endpoint(
    constructors.object_href("host_group_config", "{name}"),
    ".../update",
    method="put",
    path_params=[GROUP_NAME_FIELD],
    etag="both",
    response_schema=HostGroup,
    request_schema=UpdateHostGroupAttributes,
    permissions_required=RW_PERMISSIONS,
)
def update(params: Mapping[str, Any]) -> Response:
    """Update a host group"""
    user.need_permission("wato.edit")
    user.need_permission("wato.groups")
    name = params["name"]
    group = fetch_group(name, "host")
    constructors.require_etag(constructors.hash_of_dict(group))
    groups.edit_group(
        name,
        "host",
        updated_group_details(name, "host", params["body"]),
        pprint_value=active_config.wato_pprint_config,
    )
    group = fetch_group(name, "host")
    return serve_group(group, serialize_group("host_group_config"))


@Endpoint(
    constructors.domain_type_action_href("host_group_config", "bulk-update"),
    "cmk/bulk_update",
    method="put",
    request_schema=BulkUpdateHostGroup,
    response_schema=HostGroupCollection,
    permissions_required=RW_PERMISSIONS,
)
def bulk_update(params: Mapping[str, Any]) -> Response:
    """Bulk update host groups

    Please be aware that when doing bulk updates, it is not possible to prevent the
    [Updating Values]("lost update problem"), which is normally prevented by the ETag locking
    mechanism. Use at your own risk
    """
    user.need_permission("wato.edit")
    user.need_permission("wato.groups")
    body = params["body"]
    entries = body["entries"]
    updated_host_groups = update_groups(
        "host", entries, pprint_value=active_config.wato_pprint_config
    )
    return serve_json(serialize_group_list("host_group_config", updated_host_groups))


@Endpoint(
    constructors.object_href("host_group_config", "{name}"),
    "cmk/show",
    method="get",
    response_schema=HostGroup,
    etag="output",
    path_params=[GROUP_NAME_FIELD],
    permissions_required=PERMISSIONS,
)
def get(params: Mapping[str, Any]) -> Response:
    """Show a host group"""
    user.need_permission("wato.groups")
    name = params["name"]
    group = fetch_group(name, "host")
    return serve_group(group, serialize_group("host_group_config"))


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(create, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(bulk_create, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(list_groups, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(bulk_delete, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(update, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(bulk_update, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(get, ignore_duplicates=ignore_duplicates)
