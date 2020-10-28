#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Service groups

Service groups are a way to organize services in Checkmk and to bring order to monitoring.
By using a service group you can generate, among others, suitable views.
For example, if you want to view all file system services or update services together, you can
simply assemble service groups in a similar way as you can with host groups.

You can find an introduction to services including service groups in the
[Checkmk guide](https://checkmk.com/cms_wato_services.html).
"""

from cmk.gui import watolib
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.endpoints.utils import (
    serve_group,
    serialize_group,
    serialize_group_list,
    load_groups,
    fetch_group,
    fetch_specific_groups,
    update_groups,
)
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    response_schemas,
    request_schemas,
)
from cmk.gui.groups import load_service_group_information
from cmk.gui.plugins.openapi.restful_objects.parameters import NAME_FIELD
from cmk.gui.watolib.groups import edit_group, add_group


@Endpoint(constructors.collection_href('service_group_config'),
          'cmk/create',
          method='post',
          etag='output',
          request_schema=request_schemas.InputServiceGroup,
          response_schema=response_schemas.DomainObject)
def create(params):
    """Create a service group"""
    body = params['body']
    name = body['name']
    alias = body.get('alias')
    add_group(name, 'service', {'alias': alias})
    group = fetch_group(name, "service")
    return serve_group(group, serialize_group('service_group_config'))


@Endpoint(constructors.domain_type_action_href('service_group_config', 'bulk-create'),
          'cmk/bulk_create',
          method='post',
          request_schema=request_schemas.BulkInputServiceGroup,
          response_schema=response_schemas.DomainObjectCollection)
def bulk_create(params):
    """Bulk create service groups"""
    body = params['body']
    entries = body['entries']
    service_group_details = load_groups("service", entries)

    service_group_names = []
    for group_name, group_alias in service_group_details.items():
        add_group(group_name, 'service', {'alias': group_alias})
        service_group_names.append(group_name)

    service_groups = fetch_specific_groups(service_group_names, "service")
    return constructors.serve_json(serialize_group_list('service_group_config', service_groups))


@Endpoint(constructors.collection_href('service_group_config'),
          '.../collection',
          method='get',
          response_schema=response_schemas.DomainObjectCollection)
def list_groups(params):
    """Show all service groups"""
    return constructors.serve_json(
        serialize_group_list('service_group_config',
                             list(load_service_group_information().values())))


@Endpoint(
    constructors.object_href('service_group_config', '{name}'),
    'cmk/show',
    method='get',
    response_schema=response_schemas.ServiceGroup,
    etag='output',
    path_params=[NAME_FIELD],
)
def show_group(params):
    """Show a service group"""
    name = params['name']
    group = fetch_group(name, "service")
    return serve_group(group, serialize_group('service_group_config'))


@Endpoint(constructors.object_href('service_group_config', '{name}'),
          '.../delete',
          method='delete',
          path_params=[NAME_FIELD],
          output_empty=True,
          etag='input')
def delete(params):
    """Delete a service group"""
    name = params['name']
    group = fetch_group(name, "service")
    constructors.require_etag(constructors.etag_of_dict(group))
    watolib.delete_group(name, group_type='service')
    return Response(status=204)


@Endpoint(constructors.domain_type_action_href('service_group_config', 'bulk-delete'),
          '.../delete',
          method='delete',
          request_schema=request_schemas.BulkDeleteServiceGroup,
          output_empty=True)
def bulk_delete(params):
    """Bulk delete service groups"""
    entries = params['entries']
    for group_name in entries:
        _group = fetch_group(group_name,
                             "service",
                             status=400,
                             message="service group %s was not found" % group_name)
    for group_name in entries:
        watolib.delete_group(group_name, group_type='service')
    return Response(status=204)


@Endpoint(constructors.object_href('service_group_config', '{name}'),
          '.../update',
          method='put',
          path_params=[NAME_FIELD],
          etag='both',
          response_schema=response_schemas.ServiceGroup,
          request_schema=request_schemas.InputServiceGroup)
def update(params):
    """Update a service group"""
    name = params['name']
    group = fetch_group(name, "service")
    constructors.require_etag(constructors.etag_of_dict(group))
    edit_group(name, group_type='service', extra_info=params['body'])
    group = fetch_group(name, "service")
    return serve_group(group, serialize_group('service_group_config'))


@Endpoint(constructors.domain_type_action_href('service_group_config', 'bulk-update'),
          'cmk/bulk_update',
          method='put',
          request_schema=request_schemas.BulkUpdateServiceGroup,
          response_schema=response_schemas.DomainObjectCollection)
def bulk_update(params):
    """Bulk update service groups"""
    body = params['body']
    entries = body['entries']
    updated_service_groups = update_groups("service", entries)
    return constructors.serve_json(
        serialize_group_list('service_group_config', updated_service_groups))
