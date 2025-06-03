#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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

from collections.abc import Mapping
from typing import Any

from cmk.ccc import version

from cmk.utils import paths

from cmk.gui.config import active_config
from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.service_group_config.request_schemas import (
    BulkDeleteServiceGroup,
    BulkInputServiceGroup,
    BulkUpdateServiceGroup,
    InputServiceGroup,
    UpdateServiceGroupAttributes,
)
from cmk.gui.openapi.endpoints.service_group_config.response_schemas import (
    ServiceGroup,
    ServiceGroupCollection,
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
from cmk.gui.openapi.restful_objects import constructors, Endpoint, response_schemas
from cmk.gui.openapi.restful_objects.parameters import GROUP_NAME_FIELD
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import ProblemException, serve_json
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib import groups
from cmk.gui.watolib.groups import GroupInUseException, UnknownGroupException
from cmk.gui.watolib.groups_io import load_service_group_information

PERMISSIONS = permissions.Perm("wato.groups")

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        PERMISSIONS,
    ]
)


@Endpoint(
    constructors.collection_href("service_group_config"),
    "cmk/create",
    method="post",
    etag="output",
    request_schema=InputServiceGroup,
    response_schema=response_schemas.DomainObject,
    permissions_required=RW_PERMISSIONS,
)
def create(params: Mapping[str, Any]) -> Response:
    """Create a service group"""
    user.need_permission("wato.edit")
    user.need_permission("wato.groups")
    body = params["body"]
    name = body["name"]
    group_details = {"alias": body["alias"]}
    if version.edition(paths.omd_root) is version.Edition.CME:
        group_details = update_customer_info(group_details, body["customer"])
    groups.add_group(name, "service", group_details, pprint_value=active_config.wato_pprint_config)
    group = fetch_group(name, "service")
    return serve_group(group, serialize_group("service_group_config"))


@Endpoint(
    constructors.domain_type_action_href("service_group_config", "bulk-create"),
    "cmk/bulk_create",
    method="post",
    request_schema=BulkInputServiceGroup,
    response_schema=ServiceGroupCollection,
    permissions_required=RW_PERMISSIONS,
)
def bulk_create(params: Mapping[str, Any]) -> Response:
    """Bulk create service groups"""
    user.need_permission("wato.edit")
    user.need_permission("wato.groups")
    body = params["body"]
    entries = body["entries"]
    service_group_details = prepare_groups("service", entries)

    service_group_names = []
    for group_name, group_details in service_group_details.items():
        groups.add_group(
            group_name, "service", group_details, pprint_value=active_config.wato_pprint_config
        )
        service_group_names.append(group_name)

    service_groups = fetch_specific_groups(service_group_names, "service")
    return serve_json(serialize_group_list("service_group_config", service_groups))


@Endpoint(
    constructors.collection_href("service_group_config"),
    ".../collection",
    method="get",
    response_schema=ServiceGroupCollection,
    permissions_required=PERMISSIONS,
)
def list_groups(params: Mapping[str, Any]) -> Response:
    """Show all service groups"""
    user.need_permission("wato.groups")
    collection = build_group_list(load_service_group_information())
    return serve_json(serialize_group_list("service_group_config", collection))


@Endpoint(
    constructors.object_href("service_group_config", "{name}"),
    "cmk/show",
    method="get",
    response_schema=ServiceGroup,
    etag="output",
    path_params=[GROUP_NAME_FIELD],
    permissions_required=PERMISSIONS,
)
def show_group(params: Mapping[str, Any]) -> Response:
    """Show a service group"""
    user.need_permission("wato.groups")
    name = params["name"]
    group = fetch_group(name, "service")
    return serve_group(group, serialize_group("service_group_config"))


@Endpoint(
    constructors.object_href("service_group_config", "{name}"),
    ".../delete",
    method="delete",
    path_params=[GROUP_NAME_FIELD],
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
    additional_status_codes=[409],
)
def delete(params: Mapping[str, Any]) -> Response:
    """Delete a service group"""
    user.need_permission("wato.edit")
    user.need_permission("wato.groups")
    name = params["name"]
    try:
        groups.delete_group(
            name, group_type="service", pprint_value=active_config.wato_pprint_config
        )
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
    constructors.domain_type_action_href("service_group_config", "bulk-delete"),
    ".../delete",
    method="post",
    request_schema=BulkDeleteServiceGroup,
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
    additional_status_codes=[404, 409],
)
def bulk_delete(params: Mapping[str, Any]) -> Response:
    """Bulk delete service groups"""
    user.need_permission("wato.edit")
    user.need_permission("wato.groups")
    body = params["body"]
    for group_name in body["entries"]:
        try:
            groups.delete_group(
                group_name, group_type="service", pprint_value=active_config.wato_pprint_config
            )
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
    constructors.object_href("service_group_config", "{name}"),
    ".../update",
    method="put",
    path_params=[GROUP_NAME_FIELD],
    etag="both",
    response_schema=ServiceGroup,
    request_schema=UpdateServiceGroupAttributes,
    permissions_required=RW_PERMISSIONS,
)
def update(params: Mapping[str, Any]) -> Response:
    """Update a service group"""
    user.need_permission("wato.edit")
    user.need_permission("wato.groups")
    name = params["name"]
    group = fetch_group(name, "service")
    constructors.require_etag(constructors.hash_of_dict(group))
    groups.edit_group(
        name,
        "service",
        updated_group_details(name, "service", params["body"]),
        pprint_value=active_config.wato_pprint_config,
    )
    group = fetch_group(name, "service")
    return serve_group(group, serialize_group("service_group_config"))


@Endpoint(
    constructors.domain_type_action_href("service_group_config", "bulk-update"),
    "cmk/bulk_update",
    method="put",
    request_schema=BulkUpdateServiceGroup,
    response_schema=ServiceGroupCollection,
    permissions_required=RW_PERMISSIONS,
)
def bulk_update(params: Mapping[str, Any]) -> Response:
    """Bulk update service groups

    Please be aware that when doing bulk updates, it is not possible to prevent the
    [Updating Values]("lost update problem"), which is normally prevented by the ETag locking
    mechanism. Use at your own risk.
    """
    user.need_permission("wato.edit")
    user.need_permission("wato.groups")
    body = params["body"]
    entries = body["entries"]
    updated_service_groups = update_groups(
        "service", entries, pprint_value=active_config.wato_pprint_config
    )
    return serve_json(serialize_group_list("service_group_config", updated_service_groups))


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(create, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(bulk_create, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(list_groups, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_group, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(bulk_delete, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(update, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(bulk_update, ignore_duplicates=ignore_duplicates)
