#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Contact groups

Contact groups are the link between hosts and services on one side and users on the other.
Every contact group represents a responsibility for a specific area in the IT landscape.

You can find an introduction to user management including contact groups in the
[Checkmk guide](https://docs.checkmk.com/latest/en/wato_user.html).

### Relations

A contact group object can have the following relations present in `links`:

 * `self` - The contact group itself.
 * `urn:org.restfulobject/rels:update` - An endpoint to change this contact group.
 * `urn:org.restfulobject/rels:delete` - An endpoint to delete this contact group.

"""

from collections.abc import Iterable, Mapping
from typing import Any, cast, Literal

from cmk.ccc import version

from cmk.utils import paths

from cmk.gui.config import active_config
from cmk.gui.groups import GroupSpec
from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.contact_group_config.common import (
    APIGroupSpec,
    APIInventoryPaths,
    APIPathRestriction,
    APIPermittedPath,
)
from cmk.gui.openapi.endpoints.contact_group_config.request_schemas import (
    BulkDeleteContactGroup,
    BulkInputContactGroup,
    BulkUpdateContactGroup,
    InputContactGroup,
    UpdateContactGroupAttributes,
)
from cmk.gui.openapi.endpoints.contact_group_config.response_schemas import (
    ContactGroup,
    ContactGroupCollection,
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
from cmk.gui.openapi.permission_tracking import disable_permission_tracking
from cmk.gui.openapi.restful_objects import constructors, Endpoint, response_schemas
from cmk.gui.openapi.restful_objects.parameters import GROUP_NAME_FIELD
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import ProblemException, serve_json
from cmk.gui.session import SuperUserContext
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.groups import (
    add_group,
    check_modify_group_permissions,
    delete_group,
    edit_group,
    GroupInUseException,
    UnknownGroupException,
)
from cmk.gui.watolib.groups_io import (
    InventoryPaths,
    load_contact_group_information,
    NothingOrChoices,
    PermittedPath,
)

PERMISSIONS = permissions.Perm("wato.users")

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        PERMISSIONS,
    ]
)


def _add_path_restriction_from_api(
    out: PermittedPath, key: Literal["attributes", "columns", "nodes"], raw: APIPermittedPath
) -> None:
    match raw[key]:
        case {"type": "no_restriction"}:
            pass
        case {"type": "restrict_all"}:
            out[key] = "nothing"
        case {"type": "restrict_values", "values": values}:
            # TODO: Remove cast once https://github.com/python/mypy/pull/17600 is merged
            out[key] = "choices", cast(list[str], values)
        case unknown:
            raise ValueError(f"Unknown path restriction: {unknown}")


def _paths_from_api(raw_paths: list[APIPermittedPath]) -> Iterable[PermittedPath]:
    for raw_path in raw_paths:
        path: PermittedPath = {
            "visible_raw_path": raw_path["path"],
        }
        _add_path_restriction_from_api(path, "attributes", raw_path)
        _add_path_restriction_from_api(path, "columns", raw_path)
        _add_path_restriction_from_api(path, "nodes", raw_path)

        yield path


def _inventory_paths_from_api(inventory_paths: APIInventoryPaths | None) -> InventoryPaths:
    match inventory_paths:
        case None:
            return "allow_all"
        case {"type": "allow_all"}:
            return "allow_all"
        case {"type": "forbid_all"}:
            return "forbid_all"
        case {"type": "specific_paths", "paths": raw_paths}:
            # TODO: Remove cast once https://github.com/python/mypy/pull/17600 is merged
            return "paths", list(_paths_from_api(cast(list[APIPermittedPath], raw_paths)))
        case _:
            raise ValueError(f"Unknown inventory paths: {inventory_paths}")


def _group_from_api(group: APIGroupSpec, keep_unset: bool = False) -> GroupSpec:
    if "inventory_paths" in group or not keep_unset:
        group["inventory_paths"] = _inventory_paths_from_api(group.get("inventory_paths"))

    return group


def _path_restriction_to_api(value: NothingOrChoices | None) -> APIPathRestriction:
    match value:
        case None:
            return {"type": "no_restriction"}
        case "nothing":
            return {"type": "restrict_all"}
        case ("choices", values):
            return {"type": "restrict_values", "values": list(values)}
        case unknown:
            raise ValueError(f"Unknown path restriction: {unknown}")


def _paths_to_api(permitted_paths: Iterable[PermittedPath]) -> Iterable[APIPermittedPath]:
    for path in permitted_paths:
        yield {
            "path": path["visible_raw_path"],
            "attributes": _path_restriction_to_api(path.get("attributes")),
            "columns": _path_restriction_to_api(path.get("columns")),
            "nodes": _path_restriction_to_api(path.get("nodes")),
        }


def _inventory_paths_to_api(inventory_paths: InventoryPaths | None) -> APIInventoryPaths:
    match inventory_paths:
        case None | "allow_all":
            return {"type": "allow_all"}
        case "forbid_all":
            return {"type": "forbid_all"}
        case ("paths", permitted_paths):
            return {
                "type": "specific_paths",
                "paths": list(_paths_to_api(permitted_paths)),
            }
        case unknown:
            raise ValueError(f"Unknown inventory paths: {unknown}")


def _group_to_api(group: GroupSpec) -> APIGroupSpec:
    group["inventory_paths"] = _inventory_paths_to_api(group.get("inventory_paths"))
    return group


@Endpoint(
    constructors.collection_href("contact_group_config"),
    "cmk/create",
    method="post",
    etag="output",
    request_schema=InputContactGroup,
    response_schema=response_schemas.DomainObject,
    permissions_required=RW_PERMISSIONS,
)
def create(params: Mapping[str, Any]) -> Response:
    """Create a contact group"""
    user.need_permission("wato.edit")
    user.need_permission("wato.users")
    body = params["body"]
    name = body["name"]
    group_details = {
        "alias": body["alias"],
        "inventory_paths": _inventory_paths_from_api(body.get("inventory_paths")),
    }
    if version.edition(paths.omd_root) is version.Edition.CME:
        group_details = update_customer_info(group_details, body["customer"])
    add_group(name, "contact", group_details, pprint_value=active_config.wato_pprint_config)
    group = fetch_group(name, "contact")
    return serve_group(_group_to_api(group), serialize_group("contact_group_config"))


@Endpoint(
    constructors.domain_type_action_href("contact_group_config", "bulk-create"),
    "cmk/bulk_create",
    method="post",
    request_schema=BulkInputContactGroup,
    response_schema=ContactGroupCollection,
    permissions_required=RW_PERMISSIONS,
)
def bulk_create(params: Mapping[str, Any]) -> Response:
    """Bulk create contact groups"""
    user.need_permission("wato.edit")
    user.need_permission("wato.users")
    body = params["body"]
    entries = body["entries"]
    contact_group_details = prepare_groups("contact", entries)

    contact_group_names = []
    for group_name, group_details in contact_group_details.items():
        group_details["inventory_paths"] = _inventory_paths_from_api(
            group_details.get("inventory_paths")
        )
        add_group(
            group_name, "contact", group_details, pprint_value=active_config.wato_pprint_config
        )
        contact_group_names.append(group_name)

    contact_groups = [
        _group_to_api(group) for group in fetch_specific_groups(contact_group_names, "contact")
    ]
    return serve_json(serialize_group_list("contact_group_config", contact_groups))


@Endpoint(
    constructors.collection_href("contact_group_config"),
    ".../collection",
    method="get",
    response_schema=ContactGroupCollection,
    permissions_required=PERMISSIONS,
)
def list_group(params: Mapping[str, Any]) -> Response:
    """Show all contact groups"""
    user.need_permission("wato.users")
    collection = [
        _group_to_api(group) for group in build_group_list(load_contact_group_information())
    ]
    return serve_json(
        serialize_group_list("contact_group_config", collection),
    )


@Endpoint(
    constructors.object_href("contact_group_config", "{name}"),
    "cmk/show",
    method="get",
    response_schema=ContactGroup,
    etag="output",
    path_params=[GROUP_NAME_FIELD],
    permissions_required=PERMISSIONS,
)
def show(params: Mapping[str, Any]) -> Response:
    """Show a contact group"""
    user.need_permission("wato.users")
    name = params["name"]
    group = fetch_group(name, "contact")
    return serve_group(_group_to_api(group), serialize_group("contact_group_config"))


@Endpoint(
    constructors.object_href("contact_group_config", "{name}"),
    ".../delete",
    method="delete",
    path_params=[GROUP_NAME_FIELD],
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
    additional_status_codes=[409],
)
def delete(params: Mapping[str, Any]) -> Response:
    """Delete a contact group"""
    user.need_permission("wato.edit")
    user.need_permission("wato.users")
    name = params["name"]
    check_modify_group_permissions("contact")
    with disable_permission_tracking():
        # HACK: We need to supress this, due to lots of irrelevant dashboard permissions
        try:
            delete_group(name, "contact", pprint_value=active_config.wato_pprint_config)
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
    constructors.domain_type_action_href("contact_group_config", "bulk-delete"),
    ".../delete",
    method="post",
    request_schema=BulkDeleteContactGroup,
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
    additional_status_codes=[404, 409],
)
def bulk_delete(params: Mapping[str, Any]) -> Response:
    """Bulk delete contact groups"""
    user.need_permission("wato.edit")
    user.need_permission("wato.users")
    body = params["body"]
    with disable_permission_tracking(), SuperUserContext():
        for group_name in body["entries"]:
            # We need to supress this, because a lot of dashboard permissions are checked for
            # various reasons.
            try:
                delete_group(group_name, "contact", pprint_value=active_config.wato_pprint_config)
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
    constructors.object_href("contact_group_config", "{name}"),
    ".../update",
    method="put",
    path_params=[GROUP_NAME_FIELD],
    response_schema=ContactGroup,
    etag="both",
    request_schema=UpdateContactGroupAttributes,
    permissions_required=RW_PERMISSIONS,
)
def update(params: Mapping[str, Any]) -> Response:
    """Update a contact group"""
    user.need_permission("wato.edit")
    user.need_permission("wato.users")
    name = params["name"]
    group = fetch_group(name, "contact")
    constructors.require_etag(constructors.hash_of_dict(_group_to_api(group)))
    edit_group(
        name,
        "contact",
        updated_group_details(name, "contact", _group_from_api(params["body"], keep_unset=True)),
        pprint_value=active_config.wato_pprint_config,
    )
    group = fetch_group(name, "contact")
    return serve_group(_group_to_api(group), serialize_group("contact_group_config"))


@Endpoint(
    constructors.domain_type_action_href("contact_group_config", "bulk-update"),
    "cmk/bulk_update",
    method="put",
    request_schema=BulkUpdateContactGroup,
    response_schema=ContactGroupCollection,
    permissions_required=RW_PERMISSIONS,
)
def bulk_update(params: Mapping[str, Any]) -> Response:
    """Bulk update contact groups

    Please be aware that when doing bulk updates, it is not possible to prevent the
    [Updating Values]("lost update problem"), which is normally prevented by the ETag locking
    mechanism. Use at your own risk.
    """
    user.need_permission("wato.edit")
    user.need_permission("wato.users")
    body = params["body"]
    entries = [_group_from_api(entry, keep_unset=True) for entry in body["entries"]]
    updated_contact_groups = [
        _group_to_api(group)
        for group in update_groups(
            "contact", entries, pprint_value=active_config.wato_pprint_config
        )
    ]
    return serve_json(serialize_group_list("contact_group_config", updated_contact_groups))


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(create, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(bulk_create, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(list_group, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(bulk_delete, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(update, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(bulk_update, ignore_duplicates=ignore_duplicates)
