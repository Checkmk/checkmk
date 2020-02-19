#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import httplib

from connexion import ProblemException  # type: ignore[import]
from werkzeug.datastructures import ETags

from cmk.gui import watolib
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import response
from cmk.gui.plugins.openapi.endpoints.utils import (action_parameter, collection_object,
                                                     domain_object, link_rel, object_action_member,
                                                     object_collection_member, object_href,
                                                     object_property_member, require_etag,
                                                     serve_json, sucess)
from cmk.gui.watolib import CREFolder  # pylint: disable=unused-import
from cmk.gui.wsgi.types import DomainObject  # pylint: disable=unused-import

# TODO: Implement decorators which describe parameters and response types
# TODO: Remove all hard-coded response creation in favour of a generic one
# TODO: Implement formal description (GET endpoint) of move action

# has to store: url, inputs, outputs, name, links, domain-type
# @param('name', location='body')
# @param('title', location='body',)
# @param('parent', location='body', optional=True)
# @param('attributes', location='body', optional=True)


def create(params):
    put_body = params['body']
    name = put_body['name']
    title = put_body['title']
    parent = put_body['parent']
    attributes = put_body.get('attributes', {})

    if parent is None:
        parent_folder = watolib.Folder.root_folder()
    else:
        parent_folder = _load_folder(parent, status=400)

    folder = parent_folder.create_subfolder(name, title, attributes)

    return _serve_folder(folder)


def update(params):
    ident = params['ident']
    folder = _load_folder(ident, status=404)
    require_etag(_get_etag(folder))

    post_body = params['body']
    title = post_body['title']
    attributes = folder.attributes()
    folder.edit(title, attributes)

    return _serve_folder(folder)


def delete(params):
    ident = params['ident']
    folder = _load_folder(ident, status=404)
    parent = folder.parent()
    parent.delete_subfolder(folder.name())

    return sucess()


def move(params):
    ident = params['ident']
    folder = _load_folder(ident, status=404)

    require_etag(_get_etag(folder))

    dest = params['body']['destination']
    if dest == 'root':
        dest_folder = watolib.Folder.root_folder()
    else:
        dest_folder = _load_folder(dest, status=400)

    folder.parent().move_subfolder_to(folder, dest_folder)

    folder = _load_folder(ident, status=500)
    return _serve_folder(folder)


def list_folders(_params):
    return serve_json({
        'id': 'folders',
        'value': [
            collection_object('folders', 'folder', folder)
            for folder in watolib.Folder.root_folder().subfolders()
        ],
        'links': [link_rel('self', '/collections/folder')]
    })


def show_folder(params):
    ident = params['ident']
    folder = _load_folder(ident, status=404)
    return _serve_folder(folder)


def _get_etag(folder):
    attributes = folder.attributes()
    if 'meta_data' in attributes:
        etags = [str(attributes['meta_data']['updated_at'])]
        return ETags(strong_etags=etags)
    else:
        raise ProblemException(500, "Folder %r has no meta_data." % (folder.name(),),
                               "Can't create ETag.")


def _serve_folder(folder, profile=None):
    response.headers.add("ETag", _get_etag(folder).to_header())
    return serve_json(_serialize_folder(folder), profile=profile)


def _serialize_folder(folder):
    # type: (CREFolder) -> DomainObject
    uri = '/objects/folder/%s' % (folder.id(),)
    return domain_object(
        domain_type='folder',
        identifier=folder.id(),
        title=folder.title(),
        members=dict([
            object_collection_member(
                name='hosts',
                base=uri,
                entries=[object_href('host', host) for host in folder.hosts().values()],
            ),
            object_action_member(
                name='move',
                base=uri,
                parameters=dict([
                    action_parameter(
                        action='move',
                        parameter='destination',
                        friendly_name='The destination folder of this move action',
                        optional=False,
                        pattern="^[0-9a-fA-F]{32}|root$",
                    ),
                ]),
            ),
            object_property_member(
                name='title',
                value=folder.title(),
                base=uri,
            ),
        ]),
        extensions={
            'attributes': folder.attributes(),
        },
    )


def _load_folder(ident, status=404):
    try:
        return watolib.Folder.by_id(ident)
    except MKUserError as exc:
        raise ProblemException(status, httplib.responses[status], str(exc))
