#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
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

from cmk.ccc.exceptions import MKGeneralException

from cmk.utils.tags import AuxTag, AuxTagInUseError, TagID

from cmk.gui.config import active_config
from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.aux_tags.schemas import (
    AuxTagAttrsCreate,
    AuxTagAttrsUpdate,
    AuxTagID,
    AuxTagIDShouldExist,
    AuxTagIDShouldExistShouldBeCustom,
    AuxTagResponse,
    AuxTagResponseCollection,
)
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.openapi.utils import problem, serve_json
from cmk.gui.utils import permission_verification as permissions
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
        help=params["body"].get("help"),
    )
    try:
        tag_config.insert_aux_tag(aux_tag)
        tag_config.validate_config()

    except MKGeneralException as e:
        return problem(
            status=400,
            title="Unable to create auxiliary tag",
            detail=str(e),
        )

    update_tag_config(tag_config, pprint_value=active_config.wato_pprint_config)
    return serve_json(data=_serialize_aux_tag(aux_tag))


@Endpoint(
    constructors.object_href("aux_tag", "{aux_tag_id}"),
    "cmk/update",
    method="put",
    tag_group="Setup",
    path_params=[AuxTagIDShouldExistShouldBeCustom],
    request_schema=AuxTagAttrsUpdate,
    response_schema=AuxTagResponse,
    permissions_required=RW_PERMISSIONS,
)
def put_aux_tag(params: Mapping[str, Any]) -> Response:
    """Update an aux tag"""
    user.need_permission("wato.edit")
    user.need_permission("wato.hosttags")

    tag_config = load_tag_config()
    existing_tag = tag_config.aux_tag_list.get_aux_tag(TagID(params["aux_tag_id"]))
    aux_tag = AuxTag(
        tag_id=params["aux_tag_id"],
        title=params["body"].get("title", existing_tag.title),
        topic=params["body"].get("topic", existing_tag.topic),
        help=params["body"].get("help", existing_tag.help),
    )
    tag_config.update_aux_tag(TagID(params["aux_tag_id"]), aux_tag)
    update_tag_config(tag_config, pprint_value=active_config.wato_pprint_config)
    return serve_json(data=_serialize_aux_tag(aux_tag))


@Endpoint(
    constructors.object_action_href("aux_tag", "{aux_tag_id}", "delete"),
    ".../delete",
    method="post",
    path_params=[AuxTagID],
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
    additional_status_codes=[409],
)
def delete_aux_tag(params: Mapping[str, Any]) -> Response:
    """Delete an Auxiliary Tag"""
    user.need_permission("wato.edit")
    user.need_permission("wato.hosttags")

    tag_config = load_tag_config()
    try:
        tag_config.remove_aux_tag(TagID(params["aux_tag_id"]))
    except AuxTagInUseError as exc:
        return problem(
            status=409,
            title="Aux tag in use",
            detail=str(exc),
        )

    update_tag_config(tag_config, pprint_value=active_config.wato_pprint_config)
    return Response(status=204)


def _serialize_aux_tag(aux_tag: AuxTag) -> DomainObject:
    return constructors.domain_object(
        domain_type="aux_tag",
        identifier=aux_tag.id,
        title=aux_tag.title,
        extensions={
            "topic": "Tags" if aux_tag.topic is None else aux_tag.topic,
            "help": "" if aux_tag.help is None else aux_tag.help,
        },
        editable=True,
        deletable=True,
    )


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(show_aux_tag, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_aux_tags, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(create_aux_tag, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(put_aux_tag, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete_aux_tag, ignore_duplicates=ignore_duplicates)
