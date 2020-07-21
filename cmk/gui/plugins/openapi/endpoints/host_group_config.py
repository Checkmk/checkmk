#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Host-groups"""
import http.client

from connexion import ProblemException  # type: ignore[import]

from cmk.gui import watolib
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.endpoints.utils import (
    serve_group,
    serialize_group,
    serialize_group_list,
)
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    endpoint_schema,
    response_schemas,
    request_schemas,
)
from cmk.gui.groups import load_host_group_information
from cmk.gui.watolib.groups import edit_group, add_group


@endpoint_schema(constructors.collection_href('host_group_config'),
                 'cmk/create',
                 method='post',
                 etag='output',
                 request_body_required=True,
                 request_schema=request_schemas.InputHostGroup,
                 response_schema=response_schemas.HostGroup)
def create(params):
    """Create a host-group"""
    body = params['body']
    name = body['name']
    alias = body.get('alias')
    add_group(name, 'host', {'alias': alias})
    group = _fetch_host_group(name)
    return serve_group(group, serialize_group('host_group_config'))


@endpoint_schema(constructors.collection_href('host_group_config'),
                 '.../collection',
                 method='get',
                 response_schema=response_schemas.DomainObjectCollection)
def list_groups(params):
    """List service-groups"""
    return constructors.serve_json(
        serialize_group_list('service_group_config', list(load_host_group_information().values())))


@endpoint_schema(constructors.object_href('host_group_config', '{name}'),
                 '.../delete',
                 method='delete',
                 parameters=['name'],
                 output_empty=True,
                 etag='input')
def delete(params):
    """Delete a host-group"""
    name = params['name']
    group = _fetch_host_group(name)
    constructors.require_etag(constructors.etag_of_dict(group))
    watolib.delete_group(name, 'host')
    return Response(status=204)


@endpoint_schema(constructors.domain_type_action_href('host_group_config', 'bulk-delete'),
                 '.../delete',
                 method='delete',
                 request_schema=request_schemas.BulkDeleteHostGroup,
                 output_empty=True)
def bulk_delete(params):
    """Bulk delete host group configs"""
    # TODO: etag implementation
    entries = params['entries']
    for group_name in entries:
        message = "host group %s was not found" % group_name
        _group = _fetch_host_group(
            group_name,
            status=400,
            message=message,
        )  # TODO: etag check should be done here

    for group_name in entries:
        watolib.delete_group(group_name, 'host')
    return Response(status=204)


@endpoint_schema(constructors.object_href('host_group_config', '{name}'),
                 '.../update',
                 method='put',
                 parameters=['name'],
                 response_schema=response_schemas.HostGroup,
                 etag='both',
                 request_body_required=True,
                 request_schema=request_schemas.InputHostGroup)
def update(params):
    """Update a host-group"""
    name = params['name']
    group = _fetch_host_group(name)
    constructors.require_etag(constructors.etag_of_dict(group))
    edit_group(name, 'host', params['body'])
    group = _fetch_host_group(name)
    return serve_group(group, serialize_group('host_group_config'))


@endpoint_schema(constructors.object_href('host_group_config', '{name}'),
                 'cmk/show',
                 method='get',
                 response_schema=response_schemas.HostGroup,
                 etag='output',
                 parameters=['name'])
def get(params):
    """Show a host-group"""
    name = params['name']
    group = _fetch_host_group(name)
    return serve_group(group, serialize_group('host_group_config'))


def _fetch_host_group(ident, status=404, message=None):
    groups = load_host_group_information()
    try:
        group = groups[ident].copy()
    except KeyError as exc:
        if message is None:
            message = str(exc)
        raise ProblemException(status, http.client.responses[status], message)
    group['id'] = ident
    return group
