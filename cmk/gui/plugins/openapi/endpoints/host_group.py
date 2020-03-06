#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import hashlib
import json

from werkzeug.datastructures import ETags

from cmk.gui import watolib
from cmk.gui.globals import response
from cmk.gui.plugins.openapi.restful_objects import constructors, endpoint_schema, response_schemas
from cmk.gui.watolib.groups import load_host_group_information, edit_group, add_group


@endpoint_schema('/collections/host_group',
                 method='post',
                 etag='output',
                 request_body_required=True,
                 request_schema=response_schemas.InputHostGroup,
                 response_schema=response_schemas.HostGroup)
def create(params):
    body = params['body']
    name = body['name']
    alias = body.get('alias')
    add_group(name, 'host', {'alias': alias})
    group = _group_by_ident(name)
    return _serve_group(group)


@endpoint_schema('/objects/host_group/{name}',
                 method='delete',
                 parameters=['name'],
                 output_empty=True,
                 etag='input')
def delete(params):
    name = params['name']
    group = _group_by_ident(name)
    constructors.require_etag(_get_etag(group))
    watolib.delete_group(name, 'host')
    return constructors.sucess(status=204)


@endpoint_schema('/objects/host_group/{name}',
                 method='put',
                 parameters=['name'],
                 response_schema=response_schemas.HostGroup,
                 etag='both',
                 request_body_required=True,
                 request_schema=response_schemas.InputHostGroup)
def update(params):
    name = params['name']
    group = _group_by_ident(name)
    constructors.require_etag(_get_etag(group))
    edit_group(name, 'host', params['body'])
    group = _group_by_ident(name)
    return _serve_group(group)


@endpoint_schema('/objects/host_group/{name}',
                 method='get',
                 response_schema=response_schemas.HostGroup,
                 etag='output',
                 parameters=['name'])
def get(params):
    name = params['ident']
    group = _group_by_ident(name)
    return _serve_group(group)


def _serialize_host_group(host_group):
    ident = host_group['id']
    uri = '/object/host_group/%s' % (ident,)
    return constructors.domain_object(
        domain_type='host_group',
        identifier=ident,
        title=host_group['alias'],
        members=dict([
            constructors.object_property_member(
                name='title',
                value=host_group['alias'],  # type: ignore[attr-defined]
                base=uri,
            ),
        ]),
        extensions={},
    )


def _group_by_ident(ident):
    groups = load_host_group_information()
    group = groups[ident].copy()
    group['id'] = ident
    return group


def _serve_group(group):
    response.set_data(json.dumps(_serialize_host_group(group)))
    if response.status_code != 204:
        response.set_content_type('application/json')
    response.headers.add('ETag', _get_etag(group).to_header())
    return response._get_current_object()


def _get_etag(group):
    md5 = hashlib.md5()
    for key in sorted(group.keys()):
        md5.update(group[key])
    return ETags(strong_etags=md5.hexdigest())
