#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Folders"""
import http.client

from connexion import ProblemException  # type: ignore
from connexion import problem  # type: ignore[import]

from cmk.gui import watolib
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    endpoint_schema,
    request_schemas,
    response_schemas,
)
from cmk.gui.watolib import CREFolder
from cmk.gui.wsgi.type_defs import DomainObject

# TODO: Remove all hard-coded response creation in favour of a generic one
# TODO: Implement formal description (GET endpoint) of move action
# TODO: Replace connexion request validation with marshmallow and hand-rolled one
# TODO: throw out connexion
# TODO: add redoc.js


@endpoint_schema(constructors.collection_href('folder_config'),
                 'cmk/create',
                 method='post',
                 response_schema=response_schemas.ConcreteFolder,
                 etag='output',
                 request_body_required=True,
                 request_schema=request_schemas.CreateFolder)
def create(params):
    """Create a new folder"""
    put_body = params['body']
    name = put_body['name']
    title = put_body['title']
    parent = put_body['parent']
    attributes = put_body.get('attributes', {})

    if parent == "root":
        parent_folder = watolib.Folder.root_folder()
    else:
        parent_folder = load_folder(parent, status=400)

    folder = parent_folder.create_subfolder(name, title, attributes)

    return _serve_folder(folder)


@endpoint_schema(constructors.domain_type_action_href('folder_config', 'bulk-create'),
                 'cmk/bulk_create',
                 method='post',
                 response_schema=response_schemas.FolderCollection,
                 request_body_required=True,
                 request_schema=request_schemas.BulkCreateFolder)
def bulk_create(params):
    """Bulk create folders"""
    body = params['body']
    entries = body['entries']
    missing_folders = []
    for details in entries:
        parent = details['parent']
        try:
            load_folder(parent, status=400)
        except MKUserError:
            missing_folders.append(parent)

    if missing_folders:
        return problem(
            status=400,
            title="Missing parent folders",
            detail=f"The following parent folders do not exist: {' ,'.join(missing_folders)}")

    folders = []
    for details in entries:
        parent_folder = load_folder(details['parent'], status=400)

        folder = parent_folder.create_subfolder(
            details['name'],
            details['title'],
            details.get('attributes', {}),
        )
        folders.append(folder)

    return constructors.serve_json(_folders_collection(folders))


@endpoint_schema(constructors.object_href('folder_config', '{ident}'),
                 '.../persist',
                 method='put',
                 parameters=['ident'],
                 response_schema=response_schemas.ConcreteFolder,
                 etag='both',
                 request_body_required=True,
                 request_schema=request_schemas.UpdateFolder)
def update(params):
    """Update a folder

    Title and attributes can be updated, but there is no checking of the attributes done."""
    ident = params['ident']
    folder = load_folder(ident, status=404)
    constructors.require_etag(constructors.etag_of_obj(folder))

    post_body = params['body']
    title = post_body['title']
    attributes = folder.attributes()
    folder.edit(title, attributes)

    return _serve_folder(folder)


@endpoint_schema(constructors.object_href('folder_config', '{ident}'),
                 '.../delete',
                 method='delete',
                 parameters=['ident'],
                 output_empty=True,
                 etag='input')
def delete(params):
    """Delete a folder"""
    ident = params['ident']
    folder = load_folder(ident, status=404)
    _delete_specific(folder)
    return Response(status=204)


@endpoint_schema(constructors.domain_type_action_href('folder_config', 'bulk-delete'),
                 '.../delete',
                 method='delete',
                 request_schema=request_schemas.BulkDeleteFolder,
                 output_empty=True)
def bulk_delete(params):
    """Bulk delete folders based upon folder id"""
    # TODO: etag implementation
    entries = params['entries']
    folders = []
    for folder_ident in entries:
        folders.append(
            load_folder(
                folder_ident,
                status=400,
                message="folder config %s was not found" % folder_ident,
            ))
    for folder in folders:
        _delete_specific(folder)
    return Response(status=204)


def _delete_specific(folder):
    parent = folder.parent()
    parent.delete_subfolder(folder.name())


@endpoint_schema(constructors.object_action_href('folder_config', '{ident}', action_name='move'),
                 'cmk/move',
                 method='post',
                 parameters=['ident'],
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
    """List folders"""
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
                 parameters=['ident'])
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


def _serialize_folder(folder: CREFolder) -> DomainObject:
    uri = constructors.object_href('folder_config', folder.id())
    return constructors.domain_object(
        domain_type='folder_config',
        identifier=folder.id(),
        title=folder.title(),
        members={
            'hosts': constructors.object_collection(
                name='hosts',
                domain_type='host_config',
                entries=[
                    constructors.link_rel(
                        rel='.../value',
                        parameters={'collection': "items"},
                        href=constructors.object_href('host_config', host),
                    ) for host in folder.hosts().values()
                ],
                base=uri,
            ),
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
            'attributes': folder.attributes(),
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
