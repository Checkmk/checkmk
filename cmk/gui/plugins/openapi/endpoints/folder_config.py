#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
host inherits all attributes of it's folder and the folder's parent folders. So setting a SNMP
community in a folder is equivalent to setting the same on all hosts in said folder.

Some host endpoints allow one to view the "effective attributes", which is an aggregation of all
attributes up to the root.

### Relations

A folder_config object can have the following relations present in `links`:

 * `self` - The folder itself.
 * `urn:org.restfulobjects:rels/update` - The endpoint to update this folder.
 * `urn:org.restfulobjects:rels/delete` - The endpoint to delete this folder.


"""
from typing import List

from werkzeug.datastructures import ETags

from cmk.gui import watolib
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import Response
from cmk.gui import fields
from cmk.gui.plugins.openapi.endpoints.host_config import host_collection
from cmk.gui.plugins.openapi.endpoints.utils import folder_slug
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    request_schemas,
    response_schemas,
)
from cmk.gui.plugins.openapi.utils import ProblemException, problem
from cmk.gui.watolib import CREFolder

# TODO: Remove all hard-coded response creation in favour of a generic one
# TODO: Implement formal description (GET endpoint) of move action

PATH_FOLDER_FIELD = {
    'folder': fields.FolderField(
        description=("The path of the folder being requested. Please be aware that slashes can't "
                     "be used in the URL. Also, escaping the slashes via %2f will not work. Please "
                     "replace the path delimiters with the tilde character `~`."),
        example='~my~fine~folder',
        required=True,
    )
}


@Endpoint(constructors.collection_href('folder_config'),
          'cmk/create',
          method='post',
          etag='output',
          response_schema=response_schemas.FolderSchema,
          request_schema=request_schemas.CreateFolder)
def create(params):
    """Create a folder"""
    put_body = params['body']
    name = put_body['name']
    title = put_body['title']
    parent_folder = put_body['parent']
    attributes = put_body.get('attributes', {})

    if parent_folder.has_subfolder(name):
        raise ProblemException(status=400,
                               title="Path already exists",
                               detail=f"The path '{parent_folder.name()}/{name}' already exists.")

    folder = parent_folder.create_subfolder(name, title, attributes)

    return _serve_folder(folder)


@Endpoint(
    constructors.domain_object_collection_href('folder_config', '{folder}', 'hosts'),
    '.../collection',
    method='get',
    path_params=[PATH_FOLDER_FIELD],
    response_schema=response_schemas.HostConfigCollection,
)
def hosts_of_folder(params):
    """Show all hosts in a folder
    """
    folder: watolib.CREFolder = params['folder']
    return host_collection(folder.hosts().values())


@Endpoint(constructors.object_href('folder_config', '{folder}'),
          '.../persist',
          method='put',
          path_params=[PATH_FOLDER_FIELD],
          etag='both',
          response_schema=response_schemas.FolderSchema,
          request_schema=request_schemas.UpdateFolder)
def update(params):
    """Update a folder
    """
    folder = params['folder']
    constructors.require_etag(etag_of_folder(folder))

    post_body = params['body']
    if 'title' in post_body:
        title = post_body['title']
    else:
        title = folder.title()
    replace_attributes = post_body['attributes']
    update_attributes = post_body['update_attributes']
    remove_attributes = post_body['remove_attributes']

    attributes = folder.attributes().copy()

    if replace_attributes:
        attributes = replace_attributes

    if update_attributes:
        attributes.update(update_attributes)

    faulty_attributes = []
    for attribute in remove_attributes:
        try:
            attributes.pop(attribute)
        except KeyError:
            faulty_attributes.append(attribute)

    if faulty_attributes:
        return problem(status=400,
                       title="The folder was not updated",
                       detail=f"The following attributes did not exist and could therefore"
                       f"not be removed: {', '.join(faulty_attributes)}")

    folder.edit(title, attributes)

    return _serve_folder(folder)


@Endpoint(
    constructors.domain_type_action_href('folder_config', 'bulk-update'),
    'cmk/bulk_update',
    method='put',
    response_schema=response_schemas.FolderCollection,
    request_schema=request_schemas.BulkUpdateFolder,
)
def bulk_update(params):
    """Bulk update folders

    Please be aware that when doing bulk updates, it is not possible to prevent the
    [Updating Values]("lost update problem"), which is normally prevented by the ETag locking
    mechanism. Use at your own risk
    """
    body = params['body']
    entries = body['entries']
    folders = []

    faulty_folders = []

    for update_details in entries:
        folder = update_details['folder']
        current_title = folder.title()
        title = update_details.get("title", current_title)
        replace_attributes = update_details['attributes']
        update_attributes = update_details['update_attributes']
        remove_attributes = update_details['remove_attributes']
        attributes = folder.attributes().copy()

        if replace_attributes:
            attributes = replace_attributes

        if update_attributes:
            attributes.update(update_attributes)

        faulty_attempt = False
        for attribute in remove_attributes:
            try:
                attributes.pop(attribute)
            except KeyError:
                faulty_attempt = True
                break

        if faulty_attempt:
            faulty_folders.append(current_title)
            continue

        folder.edit(title, attributes)
        folders.append(folder)

    if faulty_folders:
        return problem(
            status=400,
            title="Some folders were not updated",
            detail=
            f"The following folders were not updated since some of the provided remove attributes did not exist: {', '.join(faulty_folders)}",
        )

    return constructors.serve_json(_folders_collection(folders, False))


@Endpoint(constructors.object_href('folder_config', '{folder}'),
          '.../delete',
          method='delete',
          path_params=[PATH_FOLDER_FIELD],
          output_empty=True)
def delete(params):
    """Delete a folder"""
    folder = params['folder']
    parent = folder.parent()
    parent.delete_subfolder(folder.name())
    return Response(status=204)


@Endpoint(constructors.object_action_href('folder_config', '{folder}', action_name='move'),
          'cmk/move',
          method='post',
          path_params=[PATH_FOLDER_FIELD],
          response_schema=response_schemas.FolderSchema,
          request_schema=request_schemas.MoveFolder,
          etag='both')
def move(params):
    """Move a folder"""
    folder: watolib.CREFolder = params['folder']
    folder_id = folder.id()

    constructors.require_etag(etag_of_folder(folder))

    dest_folder: watolib.CREFolder = params['body']['destination']

    try:
        folder.parent().move_subfolder_to(folder, dest_folder)
    except MKUserError as exc:
        raise ProblemException(
            title="Problem moving folder.",
            detail=exc.message,
            status=400,
        )
    folder = fields.FolderField.load_folder(folder_id)
    return _serve_folder(folder)


@Endpoint(
    constructors.collection_href('folder_config'),
    '.../collection',
    method='get',
    query_params=[{
        'parent': fields.FolderField(
            description="Show all sub-folders of this folder. The default is the root-folder.",
            example='/servers',
            missing=watolib.Folder.root_folder,  # because we can't load it too early.
        ),
        'recursive': fields.Boolean(
            description="List the folder (default: root) and all its sub-folders recursively.",
            example=False,
            missing=False,
        ),
        'show_hosts': fields.Boolean(
            description=("When set, all hosts that are stored in each folder will also be shown. "
                         "On large setups this may come at a performance cost, so by default this "
                         "is switched off."),
            example=False,
            missing=False,
        )
    }],
    response_schema=response_schemas.FolderCollection)
def list_folders(params):
    """Show all folders"""
    if params['recursive']:
        folders = params['parent'].all_folders_recursively()
    else:
        folders = params['parent'].subfolders()
    return constructors.serve_json(_folders_collection(folders, params['show_hosts']))


def _folders_collection(
    folders: List[CREFolder],
    show_hosts: bool,
):
    folders_ = []
    for folder in folders:
        members = {}
        if show_hosts:
            members['hosts'] = constructors.object_collection(
                name='hosts',
                domain_type='folder_config',
                entries=[
                    constructors.collection_item("host_config", {
                        "title": host,
                        "id": host
                    }) for host in folder.hosts()
                ],
                base="",
            )
        folders_.append(
            constructors.domain_object(
                domain_type='folder_config',
                identifier=folder_slug(folder),
                title=folder.title(),
                extensions={
                    'path': '/' + folder.path(),
                    'attributes': folder.attributes().copy(),
                },
                members=members,
            ))
    return constructors.collection_object(
        domain_type='folder_config',
        value=folders_,
    )


@Endpoint(
    constructors.object_href('folder_config', '{folder}'),
    'cmk/show',
    method='get',
    response_schema=response_schemas.FolderSchema,
    etag='output',
    query_params=[{
        'show_hosts': fields.Boolean(
            description=("When set, all hosts that are stored in this folder will also be shown. "
                         "On large setups this may come at a performance cost, so by default this "
                         "is switched off."),
            example=False,
            missing=False,
        )
    }],
    path_params=[PATH_FOLDER_FIELD],
)
def show_folder(params):
    """Show a folder"""
    folder = params['folder']
    return _serve_folder(folder, show_hosts=params['show_hosts'])


def _serve_folder(
    folder,
    profile=None,
    show_hosts=False,
):
    folder_json = _serialize_folder(folder, show_hosts)
    response = constructors.serve_json(folder_json, profile=profile)
    if not folder.is_root():
        response.headers.add("ETag", etag_of_folder(folder).to_header())
    return response


def _serialize_folder(folder: CREFolder, show_hosts):
    links = []

    if not folder.is_root():
        links.append(
            constructors.link_rel(
                rel='cmk/move',
                href=constructors.object_action_href(
                    "folder_config",
                    folder_slug(folder),
                    action_name='move',
                ),
                method='post',
                title='Move the folder',
            ))

    rv = constructors.domain_object(
        domain_type='folder_config',
        identifier=folder_slug(folder),
        title=folder.title(),
        extensions={
            'path': '/' + folder.path(),
            'attributes': folder.attributes().copy(),
        },
        links=links,
    )
    if show_hosts:
        rv['members']['hosts'] = constructors.collection_property(
            name='hosts',
            base=constructors.object_href('folder_config', folder_slug(folder)),
            value=[
                constructors.collection_item(
                    domain_type='host_config',
                    obj={
                        'id': host.id(),
                        'title': host.name(),
                    },
                ) for host in folder.hosts().values()
            ],
        )
    return rv


def etag_of_folder(folder: CREFolder) -> ETags:
    return constructors.etag_of_dict({
        'path': folder.path(),
        'attributes': folder.attributes(),
        'hosts': folder.host_names(),
    })
