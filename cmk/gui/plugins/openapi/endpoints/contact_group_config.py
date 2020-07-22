#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Contact-groups"""
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
    request_schemas,
    response_schemas,
)
from cmk.gui.watolib.groups import edit_group, add_group, load_contact_group_information


@endpoint_schema(constructors.collection_href('contact_group_config'),
                 'cmk/create',
                 method='post',
                 etag='output',
                 request_body_required=True,
                 request_schema=request_schemas.InputContactGroup,
                 response_schema=response_schemas.DomainObject)
def create(params):
    """Create a new contact group"""
    body = params['body']
    name = body['name']
    alias = body.get('alias')
    add_group(name, 'contact', {'alias': alias})
    group = _fetch_contact_group(name)
    return serve_group(group, serialize_group('contact_group_config'))


@endpoint_schema(constructors.collection_href('contact_group_config'),
                 '.../collection',
                 method='get',
                 response_schema=response_schemas.DomainObjectCollection)
def list_group(params):
    """List contact-groups"""
    return constructors.serve_json(
        serialize_group_list('contact_group_config',
                             list(load_contact_group_information().values())),)


@endpoint_schema(constructors.object_href('contact_group_config', '{name}'),
                 'cmk/show',
                 method='get',
                 response_schema=response_schemas.ContactGroup,
                 etag='output',
                 parameters=['name'])
def show(params):
    """Show a contact-group"""
    name = params['name']
    group = _fetch_contact_group(name)
    return serve_group(group, serialize_group('contact_group_config'))


@endpoint_schema(constructors.object_href('contact_group_config', '{name}'),
                 '.../delete',
                 method='delete',
                 parameters=['name'],
                 output_empty=True,
                 etag='input')
def delete(params):
    """Delete a contact-group"""
    name = params['name']
    group = _fetch_contact_group(name)
    constructors.require_etag(constructors.etag_of_dict(group))
    watolib.delete_group(name, 'contact')
    return Response(status=204)


@endpoint_schema(constructors.domain_type_action_href('contact_group_config', 'bulk-delete'),
                 '.../delete',
                 method='delete',
                 request_schema=request_schemas.BulkDeleteContactGroup,
                 output_empty=True)
def bulk_delete(params):
    """Bulk delete contact group configs"""
    entries = params['entries']
    for group_name in entries:
        _group = _fetch_contact_group(
            group_name,
            status=400,
            message=f"contact group {group_name} was not found",
        )
    for group_name in entries:
        watolib.delete_group(group_name, 'contact')
    return Response(status=204)


@endpoint_schema(constructors.object_href('contact_group_config', '{name}'),
                 '.../update',
                 method='put',
                 parameters=['name'],
                 response_schema=response_schemas.ContactGroup,
                 etag='both',
                 request_body_required=True,
                 request_schema=request_schemas.InputContactGroup)
def update(params):
    """Update a contact-group"""
    name = params['name']
    group = _fetch_contact_group(name)
    constructors.require_etag(constructors.etag_of_dict(group))
    edit_group(name, 'contact', params['body'])
    group = _fetch_contact_group(name)
    return serve_group(group, serialize_group('contact_group_config'))


def _fetch_contact_group(ident, status=404, message=None):
    groups = load_contact_group_information()
    try:
        group = groups[ident].copy()
    except KeyError as exc:
        if message is None:
            message = str(exc)
        raise ProblemException(status, http.client.responses[status], message)
    group['id'] = ident
    return group
