#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Folders

Folders are used in Checkmk to organize the hosts in a tree structure.
The root (or main) folder is always existing, other folders can be created manually.
If you build the tree cleverly you can use it to pass on attributes in a meaningful manner.

You can find an introduction to hosts including folders in the
[Checkmk guide](https://docs.checkmk.com/latest/en/wato_hosts.html).

Due to HTTP escaping folders are represented with the tilde character (`~`) as the path separator.

### Host and Folder attributes

Every host and folder can have "attributes" set, which determine the behavior of Checkmk. Each
host inherits all attributes of its folder and the folder's parent folders. So setting an SNMP
community in a folder is equivalent to setting the same on all hosts in said folder.

Some host endpoints allow one to view the "effective attributes", which is an aggregation of all
attributes up to the root.

### Relations

A folder_config object can have the following relations present in `links`:

 * `self` - The folder itself.
 * `urn:org.restfulobjects:rels/update` - The endpoint to update this folder.
 * `urn:org.restfulobjects:rels/delete` - The endpoint to delete this folder.


"""

from collections.abc import Mapping
from typing import Any

from werkzeug.datastructures import ETags

from cmk.gui import fields as gui_fields
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.common_fields import EXISTING_FOLDER_PATTERN
from cmk.gui.openapi.endpoints.folder_config.request_schemas import (
    BulkUpdateFolder,
    CreateFolder,
    DeleteModeField,
    MoveFolder,
    UpdateFolder,
)
from cmk.gui.openapi.endpoints.host_config import (
    EFFECTIVE_ATTRIBUTES,
    host_fields_filter,
    serve_host_collection,
)
from cmk.gui.openapi.endpoints.host_config.response_schemas import (
    FolderCollection,
    FolderSchema,
    HostConfigCollection,
)
from cmk.gui.openapi.endpoints.utils import folder_slug
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import CollectionObject, DomainObject
from cmk.gui.openapi.utils import problem, ProblemException, serve_json
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.hosts_and_folders import find_available_folder_name, Folder, folder_tree

from cmk import fields

PATH_FOLDER_FIELD = {
    "folder": gui_fields.FolderField(
        description=(
            "The path of the folder being requested. Please be aware that slashes can't "
            "be used in the URL. Also, escaping the slashes via %2f will not work. Please "
            "replace the path delimiters with the tilde character `~`."
        ),
        example="~my~fine~folder",
        required=True,
        pattern=EXISTING_FOLDER_PATTERN,
    )
}

FORCE_PARAM = {DeleteModeField.field_name(): DeleteModeField()}

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.manage_folders"),
        # If a folder to be deleted still contains hosts, the mange_hosts permission is required.
        permissions.Optional(permissions.Perm("wato.manage_hosts")),
        permissions.Optional(permissions.Perm("wato.all_folders")),
    ]
)

UPDATE_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.edit_folders"),
        permissions.Optional(permissions.Perm("wato.all_folders")),
    ]
)


@Endpoint(
    constructors.collection_href("folder_config"),
    "cmk/create",
    method="post",
    etag="output",
    response_schema=FolderSchema,
    request_schema=CreateFolder,
    permissions_required=RW_PERMISSIONS,
)
def create(params: Mapping[str, Any]) -> Response:
    """Create a folder"""
    user.need_permission("wato.edit")
    put_body = params["body"]
    name = put_body.get("name")
    title = put_body["title"]
    parent_folder: Folder = put_body["parent"]
    attributes = put_body.get("attributes", {})

    if parent_folder.has_subfolder(name):
        raise ProblemException(
            detail=f"A folder with name {name!r} already exists.",
        )

    if name is None:
        name = find_available_folder_name(title, parent_folder)

    folder = parent_folder.create_subfolder(
        name, title, attributes, pprint_value=active_config.wato_pprint_config
    )

    return _serve_folder(folder)


@Endpoint(
    constructors.domain_object_collection_href("folder_config", "{folder}", "hosts"),
    ".../collection",
    method="get",
    path_params=[PATH_FOLDER_FIELD],
    response_schema=HostConfigCollection,
    permissions_required=permissions.Optional(permissions.Perm("wato.see_all_folders")),
    query_params=[EFFECTIVE_ATTRIBUTES],
)
def hosts_of_folder(params: Mapping[str, Any]) -> Response:
    """Show all hosts in a folder"""
    folder: Folder = params["folder"]
    folder.permissions.need_permission("read")
    return serve_host_collection(
        folder.hosts().values(),
        fields_filter=host_fields_filter(
            is_collection=True,
            include_links=False,
            effective_attributes=params["effective_attributes"],
        ),
    )


@Endpoint(
    constructors.object_href("folder_config", "{folder}"),
    ".../persist",
    method="put",
    path_params=[PATH_FOLDER_FIELD],
    etag="both",
    response_schema=FolderSchema,
    request_schema=UpdateFolder,
    permissions_required=UPDATE_PERMISSIONS,
)
def update(params: Mapping[str, Any]) -> Response:
    """Update a folder"""
    user.need_permission("wato.edit")
    user.need_permission("wato.edit_folders")
    folder: Folder = params["folder"]
    constructors.require_etag(hash_of_folder(folder))

    post_body = params["body"]

    attributes = folder.attributes.copy()

    if replace_attributes := post_body.get("attributes"):
        attributes = replace_attributes

    if update_attributes := post_body.get("update_attributes"):
        attributes.update(update_attributes)

    if remove_attributes := post_body.get("remove_attributes"):
        faulty_attributes = []
        for attribute in remove_attributes:
            try:
                # Mypy can not help here with the dynamic key access
                attributes.pop(attribute)  # type: ignore[misc]
            except KeyError:
                faulty_attributes.append(attribute)

        if faulty_attributes:
            return problem(
                status=400,
                title="The folder was not updated",
                detail=f"The following attributes did not exist and could therefore"
                f"not be removed: {', '.join(faulty_attributes)}",
            )

    folder.edit(
        folder.title() if "title" not in post_body else post_body["title"],
        attributes,
        pprint_value=active_config.wato_pprint_config,
    )

    return _serve_folder(folder)


@Endpoint(
    constructors.domain_type_action_href("folder_config", "bulk-update"),
    "cmk/bulk_update",
    method="put",
    response_schema=FolderCollection,
    request_schema=BulkUpdateFolder,
    permissions_required=UPDATE_PERMISSIONS,
)
def bulk_update(params: Mapping[str, Any]) -> Response:
    """Bulk update folders

    Please be aware that when doing bulk updates, it is not possible to prevent the
    [Updating Values]("lost update problem"), which is normally prevented by the ETag locking
    mechanism. Use at your own risk
    """
    user.need_permission("wato.edit")
    user.need_permission("wato.edit_folders")
    body = params["body"]
    entries = body["entries"]
    folders = []

    faulty_folders = []
    for update_details in entries:
        folder: Folder = update_details["folder"]
        title = folder.title() if "title" not in update_details else update_details["title"]
        attributes = folder.attributes.copy()

        if replace_attributes := update_details.get("attributes"):
            attributes = replace_attributes

        if update_attributes := update_details.get("update_attributes"):
            attributes.update(update_attributes)

        if remove_attributes := update_details.get("remove_attributes"):
            faulty_attempt = False
            for attribute in remove_attributes:
                try:
                    # Mypy can not help here with the dynamic key access
                    attributes.pop(attribute)  # type: ignore[misc]
                except KeyError:
                    faulty_attempt = True
                    break

            if faulty_attempt:
                faulty_folders.append(title)
                continue

        folder.edit(title, attributes, pprint_value=active_config.wato_pprint_config)
        folders.append(folder)

    if faulty_folders:
        return problem(
            status=400,
            title="Some folders were not updated",
            detail=f"The following folders were not updated since some of the provided remove attributes did not exist: {', '.join(faulty_folders)}",
        )

    return serve_json(_folders_collection(folders))


@Endpoint(
    constructors.object_href("folder_config", "{folder}"),
    ".../delete",
    method="delete",
    path_params=[PATH_FOLDER_FIELD],
    query_params=[FORCE_PARAM],
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
    additional_status_codes=[401, 409],
)
def delete(params: Mapping[str, Any]) -> Response:
    """Delete a folder"""
    user.need_permission("wato.edit")

    folder: Folder = params["folder"]
    if (parent := folder.parent()) is None:
        raise ProblemException(
            title="Problem deleting folder.",
            detail="Deleting the root folder is not permitted.",
            status=401,
        )

    if (params["delete_mode"] != "recursive") and (not folder.is_empty() or folder.is_referenced()):
        raise ProblemException(
            title="Problem deleting folder.",
            detail="Folder is not empty or is referenced by another object. Use the force parameter to delete it.",
            status=409,
        )

    parent.delete_subfolder(folder.name())

    return Response(status=204)


@Endpoint(
    constructors.object_action_href("folder_config", "{folder}", action_name="move"),
    "cmk/move",
    method="post",
    path_params=[PATH_FOLDER_FIELD],
    response_schema=FolderSchema,
    request_schema=MoveFolder,
    etag="both",
    permissions_required=RW_PERMISSIONS,
)
def move(params: Mapping[str, Any]) -> Response:
    """Move a folder"""
    user.need_permission("wato.edit")
    folder: Folder = params["folder"]
    folder_id = folder.id()

    constructors.require_etag(hash_of_folder(folder))

    dest_folder: Folder = params["body"]["destination"]

    if folder.is_root():
        raise ProblemException(
            title="Problem moving folder",
            detail="You can't move the root folder.",
            status=400,
        )

    try:
        parent = folder.parent()
        assert parent is not None
        parent.move_subfolder_to(folder, dest_folder, pprint_value=active_config.wato_pprint_config)
    except MKUserError as exc:
        raise ProblemException(
            title="Problem moving folder.",
            detail=exc.message,
            status=400,
        )
    folder = gui_fields.FolderField.load_folder(folder_id)
    return _serve_folder(folder)


@Endpoint(
    constructors.collection_href("folder_config"),
    ".../collection",
    method="get",
    query_params=[
        {
            "parent": gui_fields.FolderField(
                description="Show all sub-folders of this folder. The default is the root-folder.",
                example="/servers",
                load_default=lambda: folder_tree().root_folder(),
            ),
            "recursive": fields.Boolean(
                description="List the folder (default: root) and all its sub-folders recursively.",
                example=False,
                load_default=False,
            ),
            "show_hosts": fields.Boolean(
                description=(
                    "When set, all hosts that are stored in each folder will also be shown. "
                    "On large setups this may come at a performance cost, so by default this "
                    "is switched off."
                ),
                example=False,
                load_default=False,
            ),
        }
    ],
    response_schema=FolderCollection,
    permissions_required=permissions.Optional(permissions.Perm("wato.see_all_folders")),
)
def list_folders(params: Mapping[str, Any]) -> Response:
    """Show all folders"""
    parent: Folder = params["parent"]
    if params["recursive"]:
        parent.need_recursive_permission("read")
        folders = parent.subfolders_recursively()
    else:
        parent.permissions.need_permission("read")
        folders = parent.subfolders()
    return serve_json(_folders_collection(folders, show_hosts=params["show_hosts"]))


def _folders_collection(
    folders: list[Folder],
    *,
    show_hosts: bool = False,
) -> CollectionObject:
    folders_ = []
    for folder in folders:
        members = {}
        if show_hosts:
            members["hosts"] = constructors.object_collection(
                name="hosts",
                domain_type="folder_config",
                entries=[
                    constructors.collection_item(
                        "host_config",
                        title=host_name,
                        identifier=host_name,
                    )
                    for host_name in folder.hosts()
                ],
                base="",
            )
        folders_.append(
            constructors.domain_object(
                domain_type="folder_config",
                identifier=folder_slug(folder),
                title=folder.title(),
                extensions={
                    "path": "/" + folder.path(),
                    "attributes": folder.attributes.copy(),
                },
                members=members,
            )
        )
    #
    return constructors.collection_object(
        domain_type="folder_config",
        value=folders_,
    )


@Endpoint(
    constructors.object_href("folder_config", "{folder}"),
    "cmk/show",
    method="get",
    response_schema=FolderSchema,
    etag="output",
    query_params=[
        {
            "show_hosts": fields.Boolean(
                description=(
                    "When set, all hosts that are stored in this folder will also be shown. "
                    "On large setups this may come at a performance cost, so by default this "
                    "is switched off."
                ),
                example=False,
                load_default=False,
            )
        }
    ],
    path_params=[PATH_FOLDER_FIELD],
    permissions_required=permissions.Optional(permissions.Perm("wato.see_all_folders")),
)
def show_folder(params: Mapping[str, Any]) -> Response:
    """Show a folder"""
    folder: Folder = params["folder"]
    folder.permissions.need_permission("read")
    return _serve_folder(folder, show_hosts=params["show_hosts"])


def _serve_folder(
    folder: Folder,
    profile: dict[str, str] | None = None,
    show_hosts: bool = False,
) -> Response:
    folder_json = _serialize_folder(folder, show_hosts)
    response = serve_json(folder_json, profile=profile)
    response.headers.add("ETag", ETags(strong_etags=[hash_of_folder(folder)]).to_header())
    return response


def _serialize_folder(folder: Folder, show_hosts: bool) -> DomainObject:
    links = []

    if not folder.is_root():
        links.append(
            constructors.link_rel(
                rel="cmk/move",
                href=constructors.object_action_href(
                    "folder_config",
                    folder_slug(folder),
                    action_name="move",
                ),
                method="post",
                title="Move the folder",
            )
        )

    rv = constructors.domain_object(
        domain_type="folder_config",
        identifier=folder_slug(folder),
        title=folder.title(),
        extensions={
            "path": "/" + folder.path(),
            "attributes": folder.attributes.copy(),
        },
        links=links,
    )
    if show_hosts:
        rv["members"]["hosts"] = constructors.collection_property(
            name="hosts",
            base=constructors.object_href("folder_config", folder_slug(folder)),
            value=[
                constructors.collection_item(
                    domain_type="host_config",
                    identifier=host.id(),
                    title=host.name(),
                )
                for host in folder.hosts().values()
            ],
        )
    return rv


def hash_of_folder(folder: Folder) -> constructors.ETagHash:
    return constructors.hash_of_dict(
        {
            "path": folder.path(),
            "attributes": folder.attributes,
            "hosts": folder.host_names(),
        }
    )


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(create, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(hosts_of_folder, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(update, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(bulk_update, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(move, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(list_folders, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_folder, ignore_duplicates=ignore_duplicates)
