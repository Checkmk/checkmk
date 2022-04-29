#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Service groups

Service groups are a way to organize services in Checkmk for monitoring.
By using a service group you can generate suitable views for overview and/or analysis,
for example, file system services of multiple hosts.

You can find an introduction to services including service groups in the
[Checkmk guide](https://docs.checkmk.com/latest/en/wato_services.html).

A service group object can have the following relations present in `links`:

 * `self` - The service group itself.
 * `urn:org.restfulobject/rels:update` - An endpoint to change this service group.
 * `urn:org.restfulobject/rels:delete` - An endpoint to delete this service group.
"""

from cmk.utils import version

import cmk.gui.watolib.groups as groups
from cmk.gui.groups import load_service_group_information
from cmk.gui.http import Response
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


@Endpoint(
    constructors.collection_href("service_group_config"),
    "cmk/create",
    method="post",
    etag="output",
    request_schema=request_schemas.InputServiceGroup,
    response_schema=response_schemas.DomainObject,
    permissions_required=PERMISSIONS,
)
def create(params):
    """Create a service group"""
    body = params["body"]
    name = body["name"]
    group_details = {"alias": body.get("alias")}
    if version.is_managed_edition():
        group_details = update_customer_info(group_details, body["customer"])
    groups.add_group(name, "service", group_details)
    group = fetch_group(name, "service")
    return serve_group(group, serialize_group("service_group_config"))


@Endpoint(
    constructors.domain_type_action_href("service_group_config", "bulk-create"),
    "cmk/bulk_create",
    method="post",
    request_schema=request_schemas.BulkInputServiceGroup,
    response_schema=response_schemas.DomainObjectCollection,
    permissions_required=PERMISSIONS,
)
def bulk_create(params):
    """Bulk create service groups"""
    body = params["body"]
    entries = body["entries"]
    service_group_details = prepare_groups("service", entries)

    service_group_names = []
    for group_name, group_details in service_group_details.items():
        groups.add_group(group_name, "service", group_details)
        service_group_names.append(group_name)

    service_groups = fetch_specific_groups(service_group_names, "service")
    return constructors.serve_json(serialize_group_list("service_group_config", service_groups))


@Endpoint(
    constructors.collection_href("service_group_config"),
    ".../collection",
    method="get",
    response_schema=response_schemas.LinkedValueDomainObjectCollection,
)
def list_groups(params):
    """Show all service groups"""
    collection = [
        {"id": k, "alias": v["alias"]} for k, v in load_service_group_information().items()
    ]
    return constructors.serve_json(serialize_group_list("service_group_config", collection))


@Endpoint(
    constructors.object_href("service_group_config", "{name}"),
    "cmk/show",
    method="get",
    response_schema=response_schemas.ServiceGroup,
    etag="output",
    path_params=[NAME_FIELD],
    permissions_required=PERMISSIONS,
)
def show_group(params):
    """Show a service group"""
    name = params["name"]
    group = fetch_group(name, "service")
    return serve_group(group, serialize_group("service_group_config"))


@Endpoint(
    constructors.object_href("service_group_config", "{name}"),
    ".../delete",
    method="delete",
    path_params=[NAME_FIELD],
    output_empty=True,
    permissions_required=PERMISSIONS,
)
def delete(params):
    """Delete a service group"""
    name = params["name"]
    groups.delete_group(name, group_type="service")
    return Response(status=204)


@Endpoint(
    constructors.domain_type_action_href("service_group_config", "bulk-delete"),
    ".../delete",
    method="post",
    request_schema=request_schemas.BulkDeleteServiceGroup,
    output_empty=True,
    permissions_required=PERMISSIONS,
)
def bulk_delete(params):
    """Bulk delete service groups"""
    body = params["body"]
    entries = body["entries"]
    for group_name in entries:
        _group = fetch_group(
            group_name, "service", status=400, message="service group %s was not found" % group_name
        )
    for group_name in entries:
        groups.delete_group(group_name, group_type="service")
    return Response(status=204)


@Endpoint(
    constructors.object_href("service_group_config", "{name}"),
    ".../update",
    method="put",
    path_params=[NAME_FIELD],
    etag="both",
    response_schema=response_schemas.ServiceGroup,
    request_schema=request_schemas.UpdateGroup,
    permissions_required=PERMISSIONS,
)
def update(params):
    """Update a service group"""
    name = params["name"]
    group = fetch_group(name, "service")
    constructors.require_etag(constructors.etag_of_dict(group))
    groups.edit_group(name, "service", updated_group_details(name, "service", params["body"]))
    group = fetch_group(name, "service")
    return serve_group(group, serialize_group("service_group_config"))


@Endpoint(
    constructors.domain_type_action_href("service_group_config", "bulk-update"),
    "cmk/bulk_update",
    method="put",
    request_schema=request_schemas.BulkUpdateServiceGroup,
    response_schema=response_schemas.DomainObjectCollection,
    permissions_required=PERMISSIONS,
)
def bulk_update(params):
    """Bulk update service groups

    Please be aware that when doing bulk updates, it is not possible to prevent the
    [Updating Values]("lost update problem"), which is normally prevented by the ETag locking
    mechanism. Use at your own risk.
    """
    body = params["body"]
    entries = body["entries"]
    updated_service_groups = update_groups("service", entries)
    return constructors.serve_json(
        serialize_group_list("service_group_config", updated_service_groups)
    )
