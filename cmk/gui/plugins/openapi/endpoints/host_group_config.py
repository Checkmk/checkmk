#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Host groups

Host groups are a way to organize hosts in Checkmk for monitoring.
By using a host group you can generate suitable views for overview and/or analysis.

You can find an introduction to hosts including host groups in the
[Checkmk guide](https://docs.checkmk.com/latest/en/wato_hosts.html).

A host group object can have the following relations present in `links`:

 * `self` - The host group itself.
 * `urn:org.restfulobject/rels:update` - An endpoint to change this host group.
 * `urn:org.restfulobject/rels:delete` - An endpoint to delete this host group.

"""
from cmk.utils import version

import cmk.gui.watolib.groups as groups
from cmk.gui.groups import load_host_group_information
from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.plugins.openapi.endpoints.utils import (
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
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    permissions,
    request_schemas,
    response_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import NAME_FIELD

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
    request_schema=request_schemas.InputHostGroup,
    response_schema=response_schemas.HostGroup,
    permissions_required=RW_PERMISSIONS,
)
def create(params):
    """Create a host group"""
    user.need_permission("wato.edit")
    body = params["body"]
    name = body["name"]
    group_details = {"alias": body.get("alias")}
    if version.is_managed_edition():
        group_details = update_customer_info(group_details, body["customer"])
    groups.add_group(name, "host", group_details)
    group = fetch_group(name, "host")
    return serve_group(group, serialize_group("host_group_config"))


@Endpoint(
    constructors.domain_type_action_href("host_group_config", "bulk-create"),
    "cmk/bulk_create",
    method="post",
    request_schema=request_schemas.BulkInputHostGroup,
    response_schema=response_schemas.DomainObjectCollection,
    permissions_required=RW_PERMISSIONS,
)
def bulk_create(params):
    """Bulk create host groups"""
    user.need_permission("wato.edit")
    body = params["body"]
    entries = body["entries"]
    host_group_details = prepare_groups("host", entries)

    host_group_names = []
    for group_name, group_details in host_group_details.items():
        groups.add_group(group_name, "host", group_details)
        host_group_names.append(group_name)

    host_groups = fetch_specific_groups(host_group_names, "host")
    return constructors.serve_json(serialize_group_list("host_group_config", host_groups))


@Endpoint(
    constructors.collection_href("host_group_config"),
    ".../collection",
    method="get",
    response_schema=response_schemas.LinkedValueDomainObjectCollection,
    permissions_required=PERMISSIONS,
)
def list_groups(params):
    """Show all host groups"""
    user.need_permission("wato.groups")
    collection = [{"id": k, "alias": v["alias"]} for k, v in load_host_group_information().items()]
    return constructors.serve_json(serialize_group_list("host_group_config", collection))


@Endpoint(
    constructors.object_href("host_group_config", "{name}"),
    ".../delete",
    method="delete",
    path_params=[NAME_FIELD],
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
)
def delete(params):
    """Delete a host group"""
    user.need_permission("wato.edit")
    name = params["name"]
    groups.delete_group(name, "host")
    return Response(status=204)


@Endpoint(
    constructors.domain_type_action_href("host_group_config", "bulk-delete"),
    ".../delete",
    method="post",
    request_schema=request_schemas.BulkDeleteHostGroup,
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
)
def bulk_delete(params):
    """Bulk delete host groups"""
    user.need_permission("wato.edit")
    body = params["body"]
    entries = body["entries"]
    for group_name in entries:
        message = "host group %s was not found" % group_name
        _group = fetch_group(
            group_name,
            "host",
            status=400,
            message=message,
        )

    for group_name in entries:
        groups.delete_group(group_name, "host")
    return Response(status=204)


@Endpoint(
    constructors.object_href("host_group_config", "{name}"),
    ".../update",
    method="put",
    path_params=[NAME_FIELD],
    etag="both",
    response_schema=response_schemas.HostGroup,
    request_schema=request_schemas.UpdateGroup,
    permissions_required=RW_PERMISSIONS,
)
def update(params):
    """Update a host group"""
    user.need_permission("wato.edit")
    name = params["name"]
    group = fetch_group(name, "host")
    constructors.require_etag(constructors.etag_of_dict(group))
    groups.edit_group(name, "host", updated_group_details(name, "host", params["body"]))
    group = fetch_group(name, "host")
    return serve_group(group, serialize_group("host_group_config"))


@Endpoint(
    constructors.domain_type_action_href("host_group_config", "bulk-update"),
    "cmk/bulk_update",
    method="put",
    request_schema=request_schemas.BulkUpdateHostGroup,
    response_schema=response_schemas.DomainObjectCollection,
    permissions_required=RW_PERMISSIONS,
)
def bulk_update(params):
    """Bulk update host groups

    Please be aware that when doing bulk updates, it is not possible to prevent the
    [Updating Values]("lost update problem"), which is normally prevented by the ETag locking
    mechanism. Use at your own risk
    """
    user.need_permission("wato.edit")
    body = params["body"]
    entries = body["entries"]
    updated_host_groups = update_groups("host", entries)
    return constructors.serve_json(serialize_group_list("host_group_config", updated_host_groups))


@Endpoint(
    constructors.object_href("host_group_config", "{name}"),
    "cmk/show",
    method="get",
    response_schema=response_schemas.HostGroup,
    etag="output",
    path_params=[NAME_FIELD],
    permissions_required=PERMISSIONS,
)
def get(params):
    """Show a host group"""
    user.need_permission("wato.groups")
    name = params["name"]
    group = fetch_group(name, "host")
    return serve_group(group, serialize_group("host_group_config"))
