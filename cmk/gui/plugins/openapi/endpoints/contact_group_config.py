#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Contact groups

Contact groups are the link between hosts and services on one side and users on the other.
Every contact group represents a responsibility for a specific area in the IT landscape.

You can find an introduction to user management including contact groups in the
[Checkmk guide](https://docs.checkmk.com/latest/en/wato_user.html).
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
    request_schemas,
    response_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import NAME_FIELD
from cmk.gui.watolib.groups import edit_group, add_group, load_contact_group_information


@Endpoint(constructors.collection_href('contact_group_config'),
          'cmk/create',
          method='post',
          etag='output',
          request_schema=request_schemas.InputContactGroup,
          response_schema=response_schemas.DomainObject)
def create(params):
    """Create a contact group"""
    body = params['body']
    name = body['name']
    alias = body.get('alias')
    add_group(name, 'contact', {'alias': alias})
    group = fetch_group(name, "contact")
    return serve_group(group, serialize_group('contact_group_config'))


@Endpoint(constructors.domain_type_action_href('contact_group_config', 'bulk-create'),
          'cmk/bulk_create',
          method='post',
          request_schema=request_schemas.BulkInputContactGroup,
          response_schema=response_schemas.DomainObjectCollection)
def bulk_create(params):
    """Bulk create host groups"""
    body = params['body']
    entries = body['entries']
    contact_group_details = load_groups("contact", entries)

    contact_group_names = []
    for group_name, group_alias in contact_group_details.items():
        add_group(group_name, 'contact', {'alias': group_alias})
        contact_group_names.append(group_name)

    contact_groups = fetch_specific_groups(contact_group_names, "contact")
    return constructors.serve_json(serialize_group_list('contact_group_config', contact_groups))


@Endpoint(constructors.collection_href('contact_group_config'),
          '.../collection',
          method='get',
          response_schema=response_schemas.DomainObjectCollection)
def list_group(params):
    """Show all contact groups"""
    collection = [{
        "id": k,
        "alias": v["alias"]
    } for k, v in load_contact_group_information().items()]
    return constructors.serve_json(serialize_group_list('contact_group_config', collection),)


@Endpoint(
    constructors.object_href('contact_group_config', '{name}'),
    'cmk/show',
    method='get',
    response_schema=response_schemas.ContactGroup,
    etag='output',
    path_params=[NAME_FIELD],
)
def show(params):
    """Show a contact group"""
    name = params['name']
    group = fetch_group(name, "contact")
    return serve_group(group, serialize_group('contact_group_config'))


@Endpoint(constructors.object_href('contact_group_config', '{name}'),
          '.../delete',
          method='delete',
          path_params=[NAME_FIELD],
          output_empty=True,
          etag='input')
def delete(params):
    """Delete a contact group"""
    name = params['name']
    group = fetch_group(name, "contact")
    constructors.require_etag(constructors.etag_of_dict(group))
    watolib.delete_group(name, 'contact')
    return Response(status=204)


@Endpoint(constructors.domain_type_action_href('contact_group_config', 'bulk-delete'),
          '.../delete',
          method='delete',
          request_schema=request_schemas.BulkDeleteContactGroup,
          output_empty=True)
def bulk_delete(params):
    """Bulk delete contact groups"""
    body = params['body']
    entries = body['entries']
    for group_name in entries:
        _group = fetch_group(
            group_name,
            "contact",
            status=400,
            message=f"contact group {group_name} was not found",
        )
    for group_name in entries:
        watolib.delete_group(group_name, 'contact')
    return Response(status=204)


@Endpoint(constructors.object_href('contact_group_config', '{name}'),
          '.../update',
          method='put',
          path_params=[NAME_FIELD],
          response_schema=response_schemas.ContactGroup,
          etag='both',
          request_schema=request_schemas.InputContactGroup)
def update(params):
    """Update a contact group"""
    name = params['name']
    group = fetch_group(name, "contact")
    constructors.require_etag(constructors.etag_of_dict(group))
    edit_group(name, 'contact', params['body'])
    group = fetch_group(name, "contact")
    return serve_group(group, serialize_group('contact_group_config'))


@Endpoint(constructors.domain_type_action_href('contact_group_config', 'bulk-update'),
          'cmk/bulk_update',
          method='put',
          request_schema=request_schemas.BulkUpdateContactGroup,
          response_schema=response_schemas.DomainObjectCollection)
def bulk_update(params):
    """Bulk update contact groups"""
    body = params['body']
    entries = body['entries']
    updated_contact_groups = update_groups("contact", entries)
    return constructors.serve_json(
        serialize_group_list('contact_group_config', updated_contact_groups))
