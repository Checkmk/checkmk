#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui import watolib
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.endpoints.utils import serve_group, serialize_group
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
    group = _fetch_host_group(name)
    return serve_group(group, serialize_group('host_group'))


@endpoint_schema('/objects/host_group/{name}',
                 method='delete',
                 parameters=['name'],
                 output_empty=True,
                 etag='input')
def delete(params):
    name = params['name']
    group = _fetch_host_group(name)
    constructors.require_etag(constructors.etag_of_dict(group))
    watolib.delete_group(name, 'host')
    return Response(status=204)


@endpoint_schema('/objects/host_group/{name}',
                 method='put',
                 parameters=['name'],
                 response_schema=response_schemas.HostGroup,
                 etag='both',
                 request_body_required=True,
                 request_schema=response_schemas.InputHostGroup)
def update(params):
    name = params['name']
    group = _fetch_host_group(name)
    constructors.require_etag(constructors.etag_of_dict(group))
    edit_group(name, 'host', params['body'])
    group = _fetch_host_group(name)
    return serve_group(group, serialize_group('host_group'))


@endpoint_schema('/objects/host_group/{name}',
                 method='get',
                 response_schema=response_schemas.HostGroup,
                 etag='output',
                 parameters=['name'])
def get(params):
    name = params['name']
    group = _fetch_host_group(name)
    return serve_group(group, serialize_group('host_group'))


def _fetch_host_group(ident):
    groups = load_host_group_information()
    group = groups[ident].copy()
    group['id'] = ident
    return group
