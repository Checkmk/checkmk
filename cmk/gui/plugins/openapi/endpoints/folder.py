#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Folders"""
import http.client

from connexion import ProblemException  # type: ignore

from cmk.gui import watolib
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.restful_objects import (response_schemas, constructors,
                                                     endpoint_schema, request_schemas)
from cmk.gui.watolib import CREFolder
from cmk.gui.wsgi.type_defs import DomainObject

# TODO: Remove all hard-coded response creation in favour of a generic one
# TODO: Implement formal description (GET endpoint) of move action
# TODO: Change scripts/check-yapf to tell which files changed
# TODO: Replace connexion request validation with marshmallow and hand-rolled one
# TODO: throw out connexion
# TODO: add redoc.js


@endpoint_schema('/collections/folder',
                 method='post',
                 response_schema=response_schemas.Folder,
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


@endpoint_schema('/objects/folder/{ident}',
                 method='put',
                 parameters=['ident'],
                 response_schema=response_schemas.Folder,
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


@endpoint_schema('/objects/folder/{ident}',
                 method='delete',
                 parameters=['ident'],
                 output_empty=True,
                 etag='input')
def delete(params):
    """Delete a folder"""
    ident = params['ident']
    folder = load_folder(ident, status=404)
    parent = folder.parent()
    parent.delete_subfolder(folder.name())

    return Response(status=204)


@endpoint_schema('/objects/folder/{ident}/actions/move/invoke',
                 method='post',
                 parameters=['ident'],
                 response_schema=response_schemas.Folder,
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


@endpoint_schema('/collections/folder',
                 method='get',
                 response_schema=response_schemas.DomainObjectCollection)
def list_folders(_params):
    """List folders"""
    return constructors.serve_json({
        'id': 'folders',
        'value': [
            constructors.collection_object('folders', 'folder', folder)
            for folder in watolib.Folder.root_folder().subfolders()
        ],
        'links': [constructors.link_rel('self', '/collections/folder')]
    })


@endpoint_schema('/objects/folder/{ident}',
                 method='get',
                 response_schema=response_schemas.Folder,
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


def _serialize_folder(folder):
    # type: (CREFolder) -> DomainObject
    uri = '/objects/folder/%s' % (folder.id(),)
    return constructors.domain_object(
        domain_type='folder',
        identifier=folder.id(),
        title=folder.title(),
        members={
            'hosts': constructors.object_collection(
                name='hosts',
                entries=[
                    constructors.link_rel(
                        rel='.../value;collection="items"',
                        href=constructors.object_href('host', host),
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
