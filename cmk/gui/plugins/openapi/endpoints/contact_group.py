#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui import watolib
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.endpoints.utils import serve_group, serialize_group
from cmk.gui.plugins.openapi.restful_objects import constructors, endpoint_schema, response_schemas
from cmk.gui.watolib.groups import edit_group, add_group, load_contact_group_information


@endpoint_schema('/collections/contact_group',
                 method='post',
                 etag='output',
                 request_body_required=True,
                 request_schema=response_schemas.InputContactGroup,
                 response_schema=response_schemas.DomainObject)
def create(params):
    """Create a new contact group"""
    body = params['body']
    name = body['name']
    alias = body.get('alias')
    add_group(name, 'contact', {'alias': alias})
    group = _fetch_contact_group(name)
    return serve_group(group, serialize_group('contact_group'))


@endpoint_schema('/collections/contact_group',
                 method='get',
                 response_schema=response_schemas.DomainObjectCollection)
def list_group(params):
    return constructors.serve_json({
        'id': 'folders',
        'value': [
            constructors.collection_object('contact_group', 'contact_group', group)
            for group in load_contact_group_information().values()
        ],
        'links': [constructors.link_rel('self', '/collections/contact_group')]
    })


@endpoint_schema('/objects/contact_group/{name}',
                 method='get',
                 response_schema=response_schemas.ContactGroup,
                 etag='output',
                 parameters=['name'])
def show(params):
    name = params['name']
    group = _fetch_contact_group(name)
    return serve_group(group, serialize_group('contact_group'))


@endpoint_schema('/objects/contact_group/{name}',
                 method='delete',
                 parameters=['name'],
                 output_empty=True,
                 etag='input')
def delete(params):
    name = params['name']
    group = _fetch_contact_group(name)
    constructors.require_etag(constructors.etag_of_dict(group))
    watolib.delete_group(name, 'contact')
    return Response(status=204)


@endpoint_schema('/objects/contact_group/{name}',
                 method='put',
                 parameters=['name'],
                 response_schema=response_schemas.ContactGroup,
                 etag='both',
                 request_body_required=True,
                 request_schema=response_schemas.InputContactGroup)
def update(params):
    name = params['name']
    group = _fetch_contact_group(name)
    constructors.require_etag(constructors.etag_of_dict(group))
    edit_group(name, 'contact', params['body'])
    group = _fetch_contact_group(name)
    return serve_group(group, serialize_group('contact_group'))


def _fetch_contact_group(ident):
    groups = load_contact_group_information()
    group = groups[ident].copy()
    group['id'] = ident
    return group
