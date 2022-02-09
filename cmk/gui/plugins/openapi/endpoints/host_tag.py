#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Host tag groups

Host tag groups are, besides the static folder structure, another more flexible way to
organize hosts in Checkmk for configuration.
A host tag group is a collection of different host tags, with each host receiving exactly one
tag from the group.

You can find an introduction to hosts including host tags and host tag groups in the
[Checkmk guide](https://docs.checkmk.com/latest/en/wato_hosts.html).
"""

import json
from typing import Any, Dict

from cmk.utils.tags import BuiltinTagConfig, TagGroup, TaggroupSpec

import cmk.gui.watolib as watolib
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    permissions,
    request_schemas,
    response_schemas,
)
from cmk.gui.plugins.openapi.utils import problem, ProblemException
from cmk.gui.watolib.tags import (
    change_host_tags_in_folders,
    edit_tag_group,
    is_builtin,
    load_tag_config,
    load_tag_group,
    OperationRemoveTagGroup,
    RepairError,
    save_tag_group,
    tag_group_exists,
    TagCleanupMode,
    update_tag_config,
)

from cmk import fields

PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.hosttags"),
        permissions.Optional(permissions.Perm("wato.all_folders")),
    ]
)


class HostTagGroupName(fields.String):
    """A field representing the host tag group"""

    default_error_messages = {
        "should_exist": "Host tag group missing: {name!r}",
    }

    def _validate(self, value):
        super()._validate(value)

        if not tag_group_exists(value, builtin_included=True):
            raise self.make_error("should_exist", name=value)


HOST_TAG_GROUP_NAME = {
    "name": HostTagGroupName(
        description="The name of the host tag group",
        example="datasource",
        pattern="[a-zA-Z_]+[-0-9a-zA-Z_]*",
        required=True,
    )
}


@Endpoint(
    constructors.collection_href("host_tag_group"),
    "cmk/create",
    method="post",
    etag="output",
    request_schema=request_schemas.InputHostTagGroup,
    response_schema=response_schemas.DomainObject,
    permissions_required=PERMISSIONS,
)
def create_host_tag_group(params):
    """Create a host tag group"""
    host_tag_group_details = params["body"]
    save_tag_group(TagGroup.from_config(host_tag_group_details))
    return _serve_host_tag_group(_retrieve_group(host_tag_group_details["id"]).get_dict_format())


@Endpoint(
    constructors.object_href("host_tag_group", "{name}"),
    "cmk/show",
    method="get",
    etag="output",
    path_params=[HOST_TAG_GROUP_NAME],
    response_schema=response_schemas.ConcreteHostTagGroup,
    permissions_required=permissions.Perm("wato.hosttags"),
)
def show_host_tag_group(params):
    """Show a host tag group"""
    ident = params["name"]
    tag_group = _retrieve_group(ident=ident)
    return _serve_host_tag_group(tag_group.get_dict_format())


@Endpoint(
    constructors.collection_href("host_tag_group"),
    ".../collection",
    method="get",
    response_schema=response_schemas.DomainObjectCollection,
    permissions_required=permissions.Perm("wato.hosttags"),
)
def list_host_tag_groups(params):
    """Show all host tag groups"""
    tag_config = load_tag_config()
    tag_config += BuiltinTagConfig()
    tag_groups_collection = {
        "id": "host_tag",
        "domainType": "host_tag_group",
        "value": [
            constructors.collection_item(
                domain_type="host_tag_group",
                title=tag_group_obj.title,
                identifier=tag_group_obj.id,
            )
            for tag_group_obj in tag_config.get_tag_groups()
        ],
        "links": [constructors.link_rel("self", constructors.collection_href("host_tag_group"))],
    }
    return constructors.serve_json(tag_groups_collection)


@Endpoint(
    constructors.object_href("host_tag_group", "{name}"),
    ".../update",
    method="put",
    etag="both",
    path_params=[HOST_TAG_GROUP_NAME],
    additional_status_codes=[401, 405],
    request_schema=request_schemas.UpdateHostTagGroup,
    permissions_required=PERMISSIONS,
    response_schema=response_schemas.ConcreteHostTagGroup,
)
def update_host_tag_group(params):
    """Update a host tag group"""
    # TODO: ident verification mechanism with ParamDict replacement
    body = params["body"]
    ident = params["name"]
    if is_builtin(ident):
        return problem(
            status=405,
            title="Built-in cannot be modified",
            detail=f"The built-in host tag group {ident} cannot be modified",
        )

    updated_details = {x: body[x] for x in body if x != "repair"}
    tag_group = _retrieve_group(ident)
    group_details = tag_group.get_dict_format()
    # This is an incremental update of the TaggroupSpec
    group_details.update(updated_details)  # type: ignore[typeddict-item]
    try:
        edit_tag_group(ident, TagGroup.from_config(group_details), allow_repair=body["repair"])
    except RepairError:
        return problem(
            status=401,
            title=f'Updating this host tag group "{ident}" requires additional authorization',
            detail=(
                "The host tag group you intend to edit is used by other instances. You must "
                "authorize Checkmk to update the relevant instances using the repair parameter"
            ),
        )
    updated_tag_group = _retrieve_group(ident)
    return _serve_host_tag_group(updated_tag_group.get_dict_format())


@Endpoint(
    constructors.object_href("host_tag_group", "{name}"),
    ".../delete",
    method="delete",
    path_params=[HOST_TAG_GROUP_NAME],
    additional_status_codes=[405],
    query_params=[request_schemas.DeleteHostTagGroup],
    permissions_required=PERMISSIONS,
    output_empty=True,
)
def delete_host_tag_group(params):
    """Delete a host tag group"""
    ident = params["name"]
    if is_builtin(ident):
        return problem(
            status=405,
            title="Built-in cannot be delete",
            detail=f"The built-in host tag group {ident} cannot be deleted",
        )

    affected = change_host_tags_in_folders(
        OperationRemoveTagGroup(ident), TagCleanupMode.CHECK, watolib.Folder.root_folder()
    )
    if any(affected):
        if not params["repair"]:
            return problem(
                status=401,
                title=f'Deleting this host tag group "{ident}" requires additional authorization',
                detail=(
                    "The host tag group you intend to delete is used by other instances. You must "
                    "authorize Checkmk to update the relevant instances using the repair parameter"
                ),
            )
        watolib.host_attributes.undeclare_host_tag_attribute(ident)
        _ = change_host_tags_in_folders(
            OperationRemoveTagGroup(ident), TagCleanupMode("delete"), watolib.Folder.root_folder()
        )

    tag_config = load_tag_config()
    tag_config.remove_tag_group(ident)
    update_tag_config(tag_config)
    return Response(status=204)


def _retrieve_group(ident: str) -> TagGroup:
    tag_group = load_tag_group(ident)
    if tag_group is None:
        raise ProblemException(
            status=500,
            title="The expected host tag group was not found",
        )
    return tag_group


def _serve_host_tag_group(tag_details: TaggroupSpec) -> Response:
    response = Response()
    response.set_data(json.dumps(serialize_host_tag_group(dict(tag_details))))
    response.set_content_type("application/json")
    response.headers.add("ETag", constructors.etag_of_dict(dict(tag_details)).to_header())
    return response


def serialize_host_tag_group(details: Dict[str, Any]):
    return constructors.domain_object(
        domain_type="host_tag_group",
        identifier=details["id"],
        title=details["title"],
        members={
            "title": constructors.object_property(
                name="title",
                value=details["title"],
                prop_format="string",
                base=constructors.object_href("host_tag_group", details["id"]),
            )
        },
        extensions={key: details[key] for key in details if key in ("topic", "tags")},
    )
