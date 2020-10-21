#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Folders

Folders are used in Checkmk to organize the hosts in a tree structure.
The root (or main) folder is always existing, other folders can be created manually.
If you build the tree cleverly you can use it to pass on attributes in a meaningful manner.

You can find an introduction to hosts including folders in the
[Checkmk guide](https://checkmk.com/cms_wato_hosts.html).
"""

import http.client

from cmk.gui import watolib
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    endpoint_schema,
    request_schemas,
    response_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import IDENT_FIELD
from cmk.gui.plugins.openapi.utils import ProblemException
from cmk.gui.watolib import CREFolder

# TODO: Remove all hard-coded response creation in favour of a generic one
# TODO: Implement formal description (GET endpoint) of move action
# TODO: add redoc.js


@endpoint_schema(constructors.collection_href('folder_config'),
                 'cmk/create',
                 method='post',
                 response_schema=response_schemas.ConcreteFolder,
                 etag='output',
                 request_body_required=True,
                 request_schema=request_schemas.CreateFolder)
def create(params):
    """Create a folder"""
    put_body = params['body']
    name = put_body['name']
    title = put_body['title']
    parent_folder = put_body['parent']
    attributes = put_body.get('attributes', {})

    folder = parent_folder.create_subfolder(name, title, attributes)

    return _serve_folder(folder)


@endpoint_schema(constructors.object_href('folder_config', '{ident}'),
                 '.../persist',
                 method='put',
                 path_params=[IDENT_FIELD],
                 response_schema=response_schemas.ConcreteFolder,
                 etag='both',
                 request_body_required=True,
                 request_schema=request_schemas.UpdateFolder)
def update(params):
    """Update a folder

    Title and attributes can be updated, but there is no checking of the attributes done"""
    ident = params['ident']
    folder = load_folder(ident, status=404)
    constructors.require_etag(constructors.etag_of_obj(folder))

    post_body = params['body']
    title = post_body['title']
    replace_attributes = post_body.get('attributes')
    update_attributes = post_body.get('update_attributes')

    attributes = folder.attributes().copy()

    if replace_attributes:
        attributes = replace_attributes

    if update_attributes:
        attributes.update(update_attributes)

    # FIXME
    # You can't update the attributes without updating the title, so the title is mandatory.
    # This shouldn't be the case though.
    folder.edit(title, attributes)

    return _serve_folder(folder)


@endpoint_schema(constructors.domain_type_action_href('folder_config', 'bulk-update'),
                 'cmk/bulk_update',
                 method='put',
                 response_schema=response_schemas.FolderCollection,
                 request_schema=request_schemas.BulkUpdateFolder)
def bulk_update(params):
    """Bulk update folders"""
    body = params['body']
    entries = body['entries']
    folders = []

    for update_details in entries:
        folder = update_details['folder']
        title = update_details['title']
        replace_attributes = update_details.get('attributes')
        update_attributes = update_details.get('update_attributes')
        attributes = folder.attributes().copy()

        if replace_attributes:
            attributes = replace_attributes

        if update_attributes:
            attributes.update(update_attributes)

        # FIXME: see above in update
        # You can't update the attributes without updating the title, so the title is mandatory.
        # This shouldn't be the case though.
        folder.edit(title, attributes)
        folders.append(folder)

    return constructors.serve_json(_folders_collection(folders))


@endpoint_schema(constructors.object_href('folder_config', '{ident}'),
                 '.../delete',
                 method='delete',
                 path_params=[
                     IDENT_FIELD,
                 ],
                 output_empty=True,
                 etag='input')
def delete(params):
    """Delete a folder"""
    ident = params['ident']
    folder = load_folder(ident, status=404)
    _delete_specific(folder)
    return Response(status=204)


def _delete_specific(folder):
    parent = folder.parent()
    parent.delete_subfolder(folder.name())


@endpoint_schema(constructors.object_action_href('folder_config', '{ident}', action_name='move'),
                 'cmk/move',
                 method='post',
                 path_params=[
                     IDENT_FIELD,
                 ],
                 response_schema=response_schemas.ConcreteFolder,
                 etag='both')
def move(params):
    """Move a folder"""
    ident = params['ident']
    folder = load_folder(ident, status=404)

    constructors.require_etag(constructors.etag_of_obj(folder))

    dest = params['body']['destination']
    if dest == 'root':
        dest_folder = watolib.Folder.root_folder()
    else:
        dest_folder = load_folder(dest, status=400)

    folder.parent().move_subfolder_to(folder, dest_folder)

    folder = load_folder(ident, status=500)
    return _serve_folder(folder)


@endpoint_schema(constructors.collection_href('folder_config'),
                 '.../collection',
                 method='get',
                 response_schema=response_schemas.FolderCollection)
def list_folders(_params):
    """Show all folders"""
    folders = watolib.Folder.root_folder().subfolders()
    return constructors.serve_json(_folders_collection(folders))


def _folders_collection(folders):
    collection_object = constructors.collection_object(
        domain_type='folder_config',
        value=[
            constructors.collection_item(
                domain_type='folder_config',
                obj={
                    'title': folder.title(),
                    'id': folder.id()
                },
            ) for folder in folders
        ],
        links=[constructors.link_rel('self', constructors.collection_href('folder_config'))],
    )
    return collection_object


@endpoint_schema(constructors.object_href('folder_config', '{ident}'),
                 'cmk/show',
                 method='get',
                 response_schema=response_schemas.ConcreteFolder,
                 etag='output',
                 path_params=[
                     IDENT_FIELD,
                 ])
def show_folder(params):
    """Show a folder"""
    ident = params['ident']
    folder = load_folder(ident, status=404)
    return _serve_folder(folder)


def _serve_folder(folder, profile=None):
    folder_json = _serialize_folder(folder)
    response = constructors.serve_json(folder_json, profile=profile)
    response.headers.add("ETag", constructors.etag_of_obj(folder).to_header())
    return response


def _serialize_folder(folder: CREFolder):
    uri = constructors.object_href('folder_config', folder.id())
    return constructors.domain_object(
        domain_type='folder_config',
        identifier=folder.id(),
        title=folder.title(),
        members={
            'move': constructors.object_action(
                name='move',
                base=uri,
                parameters=dict([
                    constructors.action_parameter(
                        action='move',
                        parameter='destination',
                        friendly_name='The destination folder of this move action',
                        optional=False,
                        pattern="[0-9a-fA-F]{32}|root",
                    ),
                ]),
            ),
        },
        extensions={
            'attributes': folder.attributes().copy(),
        },
    )


def load_folder(ident, status=404, message=None):
    try:
        if ident == 'root':
            return watolib.Folder.root_folder()
        return watolib.Folder.by_id(ident)
    except MKUserError as exc:
        if message is None:
            message = str(exc)
        raise ProblemException(status, http.client.responses[status], message)
