#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Contact groups

Contact groups are the link between hosts and services on one side and users on the other.
Every contact group represents a responsibility for a specific area in the IT landscape.

You can find an introduction to user management including contact groups in the
[Checkmk guide](https://docs.checkmk.com/latest/en/wato_user.html).

### Relations

A contact group object can have the following relations present in `links`:

 * `self` - The contact group itself.
 * `urn:org.restfulobject/rels:update` - An endpoint to change this contact group.
 * `urn:org.restfulobject/rels:delete` - An endpoint to delete this contact group.

"""
from cmk.gui import watolib
from cmk.gui.globals import user
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.endpoints.utils import (
    serve_group,
    serialize_group,
    serialize_group_list,
    prepare_groups,
    fetch_group,
    fetch_specific_groups,
    update_groups,
    update_customer_info,
    updated_group_details,
)
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    request_schemas,
    response_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import NAME_FIELD
from cmk.gui.watolib.groups import edit_group, add_group, load_contact_group_information
from cmk.utils import version


@Endpoint(constructors.collection_href('contact_group_config'),
          'cmk/create',
          method='post',
          etag='output',
          request_schema=request_schemas.InputContactGroup,
          response_schema=response_schemas.DomainObject)
def create(params):
    """Create a contact group"""
    user.need_permission("wato.edit")
    user.need_permission("wato.users")
    body = params['body']
    name = body['name']
    group_details = {"alias": body.get("alias")}
    if version.is_managed_edition():
        group_details = update_customer_info(group_details, body["customer"])
    add_group(name, 'contact', group_details)
    group = fetch_group(name, "contact")
    return serve_group(group, serialize_group('contact_group_config'))


@Endpoint(constructors.domain_type_action_href('contact_group_config', 'bulk-create'),
          'cmk/bulk_create',
          method='post',
          request_schema=request_schemas.BulkInputContactGroup,
          response_schema=response_schemas.DomainObjectCollection)
def bulk_create(params):
    """Bulk create contact groups"""
    user.need_permission("wato.edit")
    user.need_permission("wato.users")
    body = params['body']
    entries = body['entries']
    contact_group_details = prepare_groups("contact", entries)

    contact_group_names = []
    for group_name, group_details in contact_group_details.items():
        add_group(group_name, 'contact', group_details)
        contact_group_names.append(group_name)

    contact_groups = fetch_specific_groups(contact_group_names, "contact")
    return constructors.serve_json(serialize_group_list('contact_group_config', contact_groups))


@Endpoint(constructors.collection_href('contact_group_config'),
          '.../collection',
          method='get',
          response_schema=response_schemas.LinkedValueDomainObjectCollection)
def list_group(params):
    """Show all contact groups"""
    user.need_permission("wato.users")
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
    user.need_permission("wato.users")
    name = params['name']
    group = fetch_group(name, "contact")
    return serve_group(group, serialize_group('contact_group_config'))


@Endpoint(constructors.object_href('contact_group_config', '{name}'),
          '.../delete',
          method='delete',
          path_params=[NAME_FIELD],
          output_empty=True)
def delete(params):
    """Delete a contact group"""
    user.need_permission("wato.edit")
    user.need_permission("wato.users")
    name = params['name']
    watolib.delete_group(name, 'contact')
    return Response(status=204)


@Endpoint(constructors.domain_type_action_href('contact_group_config', 'bulk-delete'),
          '.../delete',
          method='post',
          request_schema=request_schemas.BulkDeleteContactGroup,
          output_empty=True)
def bulk_delete(params):
    """Bulk delete contact groups"""
    user.need_permission("wato.edit")
    user.need_permission("wato.users")
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
          request_schema=request_schemas.UpdateGroup)
def update(params):
    """Update a contact group"""
    user.need_permission("wato.edit")
    user.need_permission("wato.users")
    name = params['name']
    group = fetch_group(name, "contact")
    constructors.require_etag(constructors.etag_of_dict(group))
    edit_group(name, 'contact', updated_group_details(name, 'contact', params['body']))
    group = fetch_group(name, "contact")
    return serve_group(group, serialize_group('contact_group_config'))


@Endpoint(constructors.domain_type_action_href('contact_group_config', 'bulk-update'),
          'cmk/bulk_update',
          method='put',
          request_schema=request_schemas.BulkUpdateContactGroup,
          response_schema=response_schemas.DomainObjectCollection)
def bulk_update(params):
    """Bulk update contact groups

    Please be aware that when doing bulk updates, it is not possible to prevent the
    [Updating Values]("lost update problem"), which is normally prevented by the ETag locking
    mechanism. Use at your own risk.
    """
    user.need_permission("wato.edit")
    user.need_permission("wato.users")
    body = params['body']
    entries = body['entries']
    updated_contact_groups = update_groups("contact", entries)
    return constructors.serve_json(
        serialize_group_list('contact_group_config', updated_contact_groups))
