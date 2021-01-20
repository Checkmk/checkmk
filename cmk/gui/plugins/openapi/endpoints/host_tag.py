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
[Checkmk guide](hhttps://docs.checkmk.com/latest/en/wato_hosts.html).
"""

import json

from typing import Dict, Any

import cmk.gui.watolib as watolib

from cmk.gui.http import Response

from cmk.gui.plugins.openapi import fields
from cmk.gui.plugins.openapi.utils import problem
from cmk.gui.plugins.openapi.utils import ProblemException
from cmk.utils.tags import TagGroup
from cmk.gui.watolib.tags import (
    save_tag_group,
    load_tag_config,
    edit_tag_group,
    load_tag_group,
    update_tag_config,
    tag_group_exists,
    change_host_tags_in_folders,
    TagCleanupMode,
    OperationRemoveTagGroup,
    RepairError,
)
from cmk.gui.plugins.openapi.restful_objects import (
    Endpoint,
    request_schemas,
    response_schemas,
    constructors,
)


class HostTagGroupName(fields.String):
    """A field representing the host tag group

    """
    default_error_messages = {
        'should_exist': 'Host tag group missing: {name!r}',
    }

    def _validate(self, value):
        super()._validate(value)
        group_exists = tag_group_exists(value)
        if not group_exists:
            self.fail("should_exist", name=value)


HOST_TAG_GROUP_NAME = {
    'name': HostTagGroupName(
        description="The name of the host tag group",
        example='datasource',
        required=True,
    )
}


@Endpoint(
    constructors.collection_href('host_tag_group'),
    'cmk/create',
    method='post',
    etag='output',
    request_schema=request_schemas.InputHostTagGroup,
    response_schema=response_schemas.DomainObject,
)
def create_host_tag_group(params):
    """Create a host tag group"""
    host_tag_group_details = params['body']
    save_tag_group(TagGroup(host_tag_group_details))
    return _serve_host_tag_group(_retrieve_group(host_tag_group_details['id']).get_dict_format())


@Endpoint(
    constructors.object_href('host_tag_group', '{name}'),
    'cmk/show',
    method='get',
    etag='output',
    path_params=[HOST_TAG_GROUP_NAME],
    response_schema=response_schemas.ConcreteHostTagGroup,
)
def show_host_tag_group(params):
    """Show a host tag group"""
    ident = params['name']
    if not tag_group_exists(ident):
        return problem(
            404, f'Host tag group "{ident}" is not known.',
            'The host tag group you asked for is not known. Please check for eventual misspellings.'
        )
    tag_group = _retrieve_group(ident=ident)
    return _serve_host_tag_group(tag_group.get_dict_format())


@Endpoint(
    constructors.object_href('host_tag_group', '{name}'),
    '.../update',
    method='put',
    etag='both',
    path_params=[HOST_TAG_GROUP_NAME],
    request_schema=request_schemas.UpdateHostTagGroup,
    response_schema=response_schemas.ConcreteHostTagGroup,
)
def update_host_tag_group(params):
    """Update a host tag group"""
    # TODO: ident verification mechanism with ParamDict replacement
    body = params['body']
    updated_details = {x: body[x] for x in body if x != "repair"}
    ident = params['name']
    tag_group = _retrieve_group(ident)
    group_details = tag_group.get_dict_format()
    group_details.update(updated_details)
    try:
        edit_tag_group(ident, TagGroup(group_details), allow_repair=body['repair'])
    except RepairError:
        return problem(
            401, f'Updating this host tag group "{ident}" requires additional authorization',
            'The host tag group you intend to edit is used by other instances. You must authorize Checkmk '
            'to update the relevant instances using the repair parameter')
    updated_tag_group = _retrieve_group(ident)
    return _serve_host_tag_group(updated_tag_group.get_dict_format())


@Endpoint(
    constructors.object_href('host_tag_group', '{name}'),
    '.../delete',
    method='delete',
    etag='input',
    path_params=[HOST_TAG_GROUP_NAME],
    request_schema=request_schemas.DeleteHostTagGroup,
    output_empty=True,
)
def delete_host_tag_group(params):
    """Delete a host tag group"""
    ident = params['name']
    allow_repair = params['body'].get("repair", False)
    affected = change_host_tags_in_folders(OperationRemoveTagGroup(ident), TagCleanupMode.CHECK,
                                           watolib.Folder.root_folder())
    if any(affected):
        if not allow_repair:
            return problem(
                401, f'Deleting this host tag group "{ident}" requires additional authorization',
                'The host tag group you intend to delete is used by other instances. You must authorize Checkmk '
                'to update the relevant instances using the repair parameter')
        watolib.host_attributes.undeclare_host_tag_attribute(ident)
        _ = change_host_tags_in_folders(OperationRemoveTagGroup(ident), TagCleanupMode("delete"),
                                        watolib.Folder.root_folder())

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


def _serve_host_tag_group(tag_details: Dict[str, Any]) -> Response:
    response = Response()
    response.set_data(json.dumps(serialize_host_tag_group(tag_details)))
    response.set_content_type('application/json')
    response.headers.add('ETag', constructors.etag_of_dict(tag_details).to_header())
    return response


def serialize_host_tag_group(details: Dict[str, Any]):
    return constructors.domain_object(
        domain_type='host_tag_group',
        identifier=details['id'],
        title=details['title'],
        members={
            "title": constructors.object_property(
                name='title',
                value=details['title'],
                prop_format='string',
                base=constructors.object_href('host_tag_group', details['id']),
            )
        },
        extensions={key: details[key] for key in details if key in ('topic', 'tags')})
