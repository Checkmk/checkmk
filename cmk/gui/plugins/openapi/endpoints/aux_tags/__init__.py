#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Aux Tags

Auxiliary tags solve the following problem: Imagine that you define a host tag group Operating
System, with the tags Linux, AIX, Windows 2016, and Windows 2019. Now you want to define a rule
that should apply to all Windows hosts.

One way to do this is to define an auxiliary tag named Windows. Assign this auxiliary tag to
both Windows 2016 and Windows 2019. A host that has either tag will then always automatically
receive the auxiliary tag Windows from Checkmk. In the rules, Windows will appear as a separate
tag for resolving conditions.


"""
from collections.abc import Mapping
from typing import Any

from cmk.utils.tags import AuxTag
from cmk.utils.type_defs import TagID

from cmk.gui.globals import user
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.endpoints.aux_tags.schemas import (
    AuxTagAttrsCreate,
    AuxTagAttrsUpdate,
    AuxTagID,
    AuxTagIDShouldExist,
    AuxTagResponse,
    AuxTagResponseCollection,
)
from cmk.gui.plugins.openapi.restful_objects import constructors, Endpoint, permissions
from cmk.gui.plugins.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.plugins.openapi.utils import serve_json
from cmk.gui.watolib.tags import load_all_tag_config_read_only, load_tag_config, update_tag_config

PERMISSIONS = permissions.Perm("wato.hosttags")

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Optional(permissions.Perm("wato.all_folders")),
        PERMISSIONS,
    ]
)


@Endpoint(
    constructors.object_href("aux_tag", "{aux_tag_id}"),
    "cmk/show",
    method="get",
    tag_group="Setup",
    path_params=[AuxTagIDShouldExist],
    response_schema=AuxTagResponse,
    permissions_required=PERMISSIONS,
)
def show_aux_tag(params: Mapping[str, Any]) -> Response:
    """Show an Auxiliary Tag"""
    user.need_permission("wato.hosttags")

    tag_id = TagID(params["aux_tag_id"])
    aux_tags = load_all_tag_config_read_only().aux_tag_list
    aux_tag = aux_tags.get_aux_tag(tag_id)
    return serve_json(data=_serialize_aux_tag(aux_tag))


@Endpoint(
    constructors.collection_href("aux_tag"),
    ".../collection",
    method="get",
    tag_group="Setup",
    response_schema=AuxTagResponseCollection,
    update_config_generation=False,
    permissions_required=PERMISSIONS,
)
def show_aux_tags(params: Mapping[str, Any]) -> Response:
    """Show Auxiliary Tags"""
    user.need_permission("wato.hosttags")

    return serve_json(
        constructors.collection_object(
            domain_type="aux_tag",
            value=[_serialize_aux_tag(tag) for tag in load_all_tag_config_read_only().aux_tag_list],
        )
    )


@Endpoint(
    constructors.collection_href("aux_tag"),
    "cmk/create",
    method="post",
    tag_group="Setup",
    request_schema=AuxTagAttrsCreate,
    response_schema=AuxTagResponse,
    permissions_required=RW_PERMISSIONS,
)
def create_aux_tag(params: Mapping[str, Any]) -> Response:
    """Create an Auxiliary Tag"""
    user.need_permission("wato.edit")
    user.need_permission("wato.hosttags")

    tag_config = load_tag_config()
    aux_tag = AuxTag(
        tag_id=params["body"]["aux_tag_id"],
        title=params["body"]["title"],
        topic=params["body"].get("topic"),
    )
    tag_config.insert_aux_tag(aux_tag)
    update_tag_config(tag_config)
    return serve_json(data=_serialize_aux_tag(aux_tag))


@Endpoint(
    constructors.object_href("aux_tag", "{aux_tag_id}"),
    "cmk/update",
    method="put",
    tag_group="Setup",
    path_params=[AuxTagID],
    request_schema=AuxTagAttrsUpdate,
    response_schema=AuxTagResponse,
    permissions_required=RW_PERMISSIONS,
)
def put_aux_tag(params: Mapping[str, Any]) -> Response:
    """Update an aux tag"""
    user.need_permission("wato.edit")
    user.need_permission("wato.hosttags")

    tag_config = load_tag_config()
    aux_tag = AuxTag(
        tag_id=params["aux_tag_id"],
        title=params["body"].get("title"),
        topic=params["body"].get("topic"),
    )
    tag_config.update_aux_tag(TagID(params["aux_tag_id"]), aux_tag)
    update_tag_config(tag_config)
    return serve_json(data=_serialize_aux_tag(aux_tag))


@Endpoint(
    constructors.object_action_href("aux_tag", "{aux_tag_id}", "delete"),
    ".../delete",
    method="post",
    path_params=[AuxTagID],
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
)
def delete_aux_tag(params: Mapping[str, Any]) -> Response:
    """Delete an Auxiliary Tag"""
    user.need_permission("wato.edit")
    user.need_permission("wato.hosttags")

    tag_config = load_tag_config()
    tag_config.remove_aux_tag(TagID(params["aux_tag_id"]))
    update_tag_config(tag_config)
    return Response(status=204)


def _serialize_aux_tag(aux_tag: AuxTag) -> DomainObject:
    return constructors.domain_object(
        domain_type="aux_tag",
        identifier=aux_tag.id,
        title=aux_tag.title,
        extensions={
            "topic": "Tags" if aux_tag.topic is None else aux_tag.topic,
        },
        editable=True,
        deletable=True,
    )
