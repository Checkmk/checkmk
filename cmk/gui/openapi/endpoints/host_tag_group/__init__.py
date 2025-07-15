#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
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

from collections.abc import Mapping
from typing import Any

from cmk.utils.regex import REGEX_ID
from cmk.utils.tags import BuiltinTagConfig, TagGroup, TagGroupID, TagGroupSpec

from cmk.gui.config import active_config
from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.host_tag_group.request_schemas import (
    DeleteHostTagGroup,
    InputHostTagGroup,
    UpdateHostTagGroup,
)
from cmk.gui.openapi.endpoints.host_tag_group.response_schemas import (
    ConcreteHostTagGroup,
    HostTagGroupCollection,
)
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.openapi.utils import problem, ProblemException, serve_json
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.tags import (
    change_host_tags,
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

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
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
        pattern=REGEX_ID,
        required=True,
    )
}


@Endpoint(
    constructors.collection_href("host_tag_group"),
    "cmk/create",
    method="post",
    etag="output",
    request_schema=InputHostTagGroup,
    response_schema=ConcreteHostTagGroup,
    permissions_required=RW_PERMISSIONS,
)
def create_host_tag_group(params: Mapping[str, Any]) -> Response:
    """Create a host tag group"""
    user.need_permission("wato.edit")
    host_tag_group_details = params["body"]
    save_tag_group(
        TagGroup.from_config(host_tag_group_details),
        pprint_value=active_config.wato_pprint_config,
    )
    return _serve_host_tag_group(_retrieve_group(host_tag_group_details["id"]).get_dict_format())


@Endpoint(
    constructors.object_href("host_tag_group", "{name}"),
    "cmk/show",
    method="get",
    etag="output",
    path_params=[HOST_TAG_GROUP_NAME],
    response_schema=ConcreteHostTagGroup,
    permissions_required=PERMISSIONS,
)
def show_host_tag_group(params: Mapping[str, Any]) -> Response:
    """Show a host tag group"""
    ident = params["name"]
    user.need_permission("wato.hosttags")
    tag_group = _retrieve_group(ident=ident)
    return _serve_host_tag_group(tag_group.get_dict_format())


@Endpoint(
    constructors.collection_href("host_tag_group"),
    ".../collection",
    method="get",
    response_schema=HostTagGroupCollection,
    permissions_required=PERMISSIONS,
)
def list_host_tag_groups(params: Mapping[str, Any]) -> Response:
    """Show all host tag groups"""
    user.need_permission("wato.hosttags")
    tag_config = load_tag_config()
    tag_config += BuiltinTagConfig()
    tag_groups_collection = {
        "id": "host_tag",
        "domainType": "host_tag_group",
        "value": [
            serialize_host_tag_group(tag_group_obj.get_dict_format())
            for tag_group_obj in tag_config.get_tag_groups()
        ],
        "links": [constructors.link_rel("self", constructors.collection_href("host_tag_group"))],
    }
    return serve_json(tag_groups_collection)


@Endpoint(
    constructors.object_href("host_tag_group", "{name}"),
    ".../update",
    method="put",
    etag="both",
    path_params=[HOST_TAG_GROUP_NAME],
    additional_status_codes=[401, 405],
    request_schema=UpdateHostTagGroup,
    permissions_required=RW_PERMISSIONS,
    response_schema=ConcreteHostTagGroup,
)
def update_host_tag_group(params: Mapping[str, Any]) -> Response:
    """Update a host tag group"""
    # TODO: ident verification mechanism with ParamDict replacement
    user.need_permission("wato.edit")
    user.need_permission("wato.hosttags")  # see cmk.gui.wato.pages.tags
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
    # This is an incremental update of the TagGroupSpec
    group_details.update(updated_details)  # type: ignore[typeddict-item]
    try:
        edit_tag_group(
            ident,
            TagGroup.from_config(group_details),
            allow_repair=body["repair"],
            pprint_value=active_config.wato_pprint_config,
            debug=active_config.debug,
        )
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
    additional_status_codes=[401, 405],
    query_params=[DeleteHostTagGroup],
    permissions_required=RW_PERMISSIONS,
    output_empty=True,
)
def delete_host_tag_group(params: Mapping[str, Any]) -> Response:
    """Delete a host tag group"""
    user.need_permission("wato.edit")
    ident = params["name"]
    if params["repair"] and params["mode"]:
        return problem(
            status=400,
            title="Cannot use both repair and mode",
            detail="Cannot use both repair and mode at the same time",
        )
    if is_builtin(ident):
        return problem(
            status=405,
            title="Built-in cannot be delete",
            detail=f"The built-in host tag group {ident} cannot be deleted",
        )

    affected = change_host_tags(
        OperationRemoveTagGroup(ident),
        TagCleanupMode.CHECK,
        pprint_value=active_config.wato_pprint_config,
        debug=active_config.debug,
    )
    if any(affected):
        mode = TagCleanupMode(params["mode"] or ("delete" if params["repair"] else "abort"))
        if mode == TagCleanupMode.ABORT:
            affected_folder, affected_hosts, affected_rulesets = affected
            affected_occurrences = []

            if affected_folder:
                affected_occurrences.append(
                    f"folders ({', '.join(f.name() for f in affected_folder)})"
                )
            if affected_hosts:
                affected_occurrences.append(
                    f"hosts ({', '.join(h.name() for h in affected_hosts)})"
                )
            if affected_rulesets:
                affected_occurrences.append(
                    f"rulesets ({', '.join(r.name for r in affected_rulesets)})"
                )

            return problem(
                status=401,
                title=f'Deleting this host tag group "{ident}" requires additional authorization',
                detail=(
                    f"The host tag group you intend to delete is used in the following occurrences: {', '.join(affected_occurrences)}. You must "
                    "authorize Checkmk to update the relevant instances using the repair or mode parameters"
                ),
            )
        _ = change_host_tags(
            OperationRemoveTagGroup(ident),
            mode,
            pprint_value=active_config.wato_pprint_config,
            debug=active_config.debug,
        )

    tag_config = load_tag_config()
    tag_config.remove_tag_group(ident)
    update_tag_config(tag_config, pprint_value=active_config.wato_pprint_config)
    return Response(status=204)


def _retrieve_group(ident: TagGroupID) -> TagGroup:
    tag_group = load_tag_group(ident)
    if tag_group is None:
        raise ProblemException(
            status=500,
            title="Tag group not found",
            detail="The expected host tag group was not found",
        )
    return tag_group


def _serve_host_tag_group(tag_details: TagGroupSpec) -> Response:
    response = serve_json(serialize_host_tag_group(tag_details))
    return constructors.response_with_etag_created_from_dict(response, dict(tag_details))


def serialize_host_tag_group(details: TagGroupSpec) -> DomainObject:
    extensions = {
        "topic": details.get("topic", "Tags"),
        "tags": details["tags"],
    }
    if details.get("help") is not None:
        extensions.update({"help": details["help"]})

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
        extensions=extensions,
    )


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(create_host_tag_group, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_host_tag_group, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(list_host_tag_groups, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(update_host_tag_group, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete_host_tag_group, ignore_duplicates=ignore_duplicates)
