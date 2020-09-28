#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Host groups"""
from cmk.gui import watolib
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.endpoints.utils import (
    serve_group,
    serialize_group,
    serialize_group_list,
    fetch_group,
    fetch_specific_groups,
    load_groups,
    update_groups,
)
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    endpoint_schema,
    response_schemas,
    request_schemas,
)
from cmk.gui.groups import load_host_group_information
from cmk.gui.plugins.openapi.restful_objects.parameters import NAME_FIELD
from cmk.gui.watolib.groups import edit_group, add_group


@endpoint_schema(constructors.collection_href('host_group_config'),
                 'cmk/create',
                 method='post',
                 etag='output',
                 request_body_required=True,
                 request_schema=request_schemas.InputHostGroup,
                 response_schema=response_schemas.HostGroup)
def create(params):
    """Create a host group"""
    body = params['body']
    name = body['name']
    alias = body.get('alias')
    add_group(name, 'host', {'alias': alias})
    group = fetch_group(name, "host")
    return serve_group(group, serialize_group('host_group_config'))


@endpoint_schema(constructors.domain_type_action_href('host_group_config', 'bulk-create'),
                 'cmk/bulk_create',
                 method='post',
                 request_schema=request_schemas.BulkInputHostGroup,
                 response_schema=response_schemas.DomainObjectCollection)
def bulk_create(params):
    """Bulk create host groups"""
    body = params['body']
    entries = body['entries']
    host_group_details = load_groups('host', entries)

    host_group_names = []
    for group_name, group_alias in host_group_details.items():
        add_group(group_name, 'host', {'alias': group_alias})
        host_group_names.append(group_name)

    host_groups = fetch_specific_groups(host_group_names, "host")
    return constructors.serve_json(serialize_group_list('host_group_config', host_groups))


@endpoint_schema(constructors.collection_href('host_group_config'),
                 '.../collection',
                 method='get',
                 response_schema=response_schemas.DomainObjectCollection)
def list_groups(params):
    """Show all host groups"""
    return constructors.serve_json(
        serialize_group_list('service_group_config', list(load_host_group_information().values())))


@endpoint_schema(constructors.object_href('host_group_config', '{name}'),
                 '.../delete',
                 method='delete',
                 path_params=[NAME_FIELD],
                 output_empty=True,
                 etag='input')
def delete(params):
    """Delete a host group"""
    name = params['name']
    group = fetch_group(name, "host")
    constructors.require_etag(constructors.etag_of_dict(group))
    watolib.delete_group(name, 'host')
    return Response(status=204)


@endpoint_schema(constructors.domain_type_action_href('host_group_config', 'bulk-delete'),
                 '.../delete',
                 method='delete',
                 request_schema=request_schemas.BulkDeleteHostGroup,
                 output_empty=True)
def bulk_delete(params):
    """Bulk delete host groups"""
    # TODO: etag implementation
    entries = params['entries']
    for group_name in entries:
        message = "host group %s was not found" % group_name
        _group = fetch_group(
            group_name,
            "host",
            status=400,
            message=message,
        )  # TODO: etag check should be done here

    for group_name in entries:
        watolib.delete_group(group_name, 'host')
    return Response(status=204)


@endpoint_schema(constructors.object_href('host_group_config', '{name}'),
                 '.../update',
                 method='put',
                 path_params=[NAME_FIELD],
                 response_schema=response_schemas.HostGroup,
                 etag='both',
                 request_body_required=True,
                 request_schema=request_schemas.InputHostGroup)
def update(params):
    """Update a host group"""
    name = params['name']
    group = fetch_group(name, "host")
    constructors.require_etag(constructors.etag_of_dict(group))
    edit_group(name, 'host', params['body'])
    group = fetch_group(name, "host")
    return serve_group(group, serialize_group('host_group_config'))


@endpoint_schema(constructors.domain_type_action_href('host_group_config', 'bulk-update'),
                 'cmk/bulk_update',
                 method='put',
                 request_schema=request_schemas.BulkUpdateHostGroup,
                 response_schema=response_schemas.DomainObjectCollection)
def bulk_update(params):
    """Bulk update host groups"""
    body = params['body']
    entries = body['entries']
    updated_host_groups = update_groups("host", entries)
    return constructors.serve_json(serialize_group_list('host_group_config', updated_host_groups))


@endpoint_schema(constructors.object_href('host_group_config', '{name}'),
                 'cmk/show',
                 method='get',
                 response_schema=response_schemas.HostGroup,
                 etag='output',
                 path_params=[NAME_FIELD])
def get(params):
    """Show a host group"""
    name = params['name']
    group = fetch_group(name, "host")
    return serve_group(group, serialize_group('host_group_config'))
