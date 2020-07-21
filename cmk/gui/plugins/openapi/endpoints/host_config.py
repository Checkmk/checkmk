#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Hosts

Hosts can only exist in conjunction with Folders. To get a list of hosts
you need to access the folder API endpoints.
"""
import json

from connexion import problem  # type: ignore[import]

from cmk.gui import watolib
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.endpoints.folder_config import load_folder
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    endpoint_schema,
    request_schemas,
    response_schemas,
)
from cmk.gui.plugins.webapi import check_hostname, validate_host_attributes


@endpoint_schema(constructors.collection_href('host_config'),
                 'cmk/create',
                 method='post',
                 etag='output',
                 request_body_required=True,
                 request_schema=request_schemas.CreateHost,
                 response_schema=response_schemas.ConcreteHost)
def create_host(params):
    """Create a host"""
    body = params['body']
    host_name = body['host_name']
    folder_id = body['folder']
    attributes = body.get('attributes', {})
    cluster_nodes = body.get('nodes', [])

    check_hostname(host_name, should_exist=False)
    for node in cluster_nodes:
        check_hostname(node, should_exist=True)

    validate_host_attributes(attributes, new=True)

    if folder_id == 'root':
        folder = watolib.Folder.root_folder()
    else:
        folder = load_folder(folder_id, status=400)

    folder.create_hosts([(host_name, attributes, cluster_nodes)])

    host = watolib.Host.host(host_name)
    return _serve_host(host)


@endpoint_schema(constructors.collection_href('host_config'),
                 '.../collection',
                 method='get',
                 response_schema=response_schemas.HostCollection)
def list_hosts(param):
    """List all hosts"""
    return constructors.serve_json({
        'id': 'host',
        'value': [
            constructors.collection_item(
                domain_type='host',
                obj={
                    'title': host.name(),
                    'id': host.id()
                },
            ) for host in watolib.Folder.root_folder().all_hosts_recursively().values()
        ],
        'links': [constructors.link_rel('self', constructors.collection_href('host_config'))],
    })


@endpoint_schema(constructors.object_href('host_config', '{host_name}'),
                 '.../update',
                 method='put',
                 parameters=['host_name'],
                 etag='both',
                 request_body_required=True,
                 request_schema=request_schemas.UpdateHost,
                 response_schema=response_schemas.ConcreteHost)
def update_host(params):
    """Update a host"""
    host_name = params['host_name']
    body = params['body']
    attributes = body['attributes']
    host: watolib.CREHost = watolib.Host.host(host_name)
    constructors.require_etag(constructors.etag_of_obj(host))
    validate_host_attributes(attributes, new=False)
    host.update_attributes(attributes)
    return _serve_host(host)


@endpoint_schema(constructors.object_href('host_config', '{host_name}'),
                 '.../delete',
                 method='delete',
                 parameters=['host_name'],
                 etag='input',
                 request_body_required=False,
                 output_empty=True)
def delete(params):
    """Delete a host"""
    host_name = params['host_name']
    check_hostname(host_name, should_exist=True)
    host = watolib.Host.host(host_name)
    constructors.require_etag(constructors.etag_of_obj(host))
    host.folder().delete_hosts([host.name()])
    return Response(status=204)


@endpoint_schema(constructors.domain_type_action_href('host_config', 'bulk-delete'),
                 '.../delete',
                 method='delete',
                 request_schema=request_schemas.BulkDeleteHost,
                 output_empty=True)
def bulk_delete(params):
    """Bulk delete hosts based upon host names"""
    # TODO: require etag checking (409 Response)
    entries = params['entries']
    for host_name in entries:
        check_hostname(host_name, should_exist=True)

    for host_name in entries:
        host = watolib.Host.host(host_name)
        host.folder().delete_hosts([host.name()])
    return Response(status=204)


@endpoint_schema(constructors.object_href('host_config', '{host_name}'),
                 'cmk/show',
                 method='get',
                 parameters=['host_name'],
                 etag='output',
                 response_schema=response_schemas.ConcreteHost)
def show_host(params):
    """Show a host"""
    host_name = params['host_name']
    host = watolib.Host.host(host_name)
    if host is None:
        return problem(
            404, f'Host "{host_name}" is not known.',
            'The host you asked for is not known. Please check for eventual misspellings.')
    return _serve_host(host)


def _serve_host(host):
    response = Response()
    response.set_data(json.dumps(serialize_host(host)))
    response.set_content_type('application/json')
    response.headers.add('ETag', constructors.etag_of_obj(host).to_header())
    return response


def serialize_host(host):
    base = constructors.object_href('host_config', host.ident())
    members = constructors.DomainObjectMembers(base)
    members.object_property(
        name='folder_config',
        value=constructors.object_href('folder_config',
                                       host.folder().id()),
        prop_format='string',
    )

    attributes = host.attributes().copy()
    del attributes['meta_data']

    return constructors.domain_object(
        domain_type='host_config',
        identifier=host.id(),
        title=host.alias(),
        members=members.to_dict(),
        extensions={
            'attributes': attributes,
            'is_cluster': host.is_cluster(),
            'is_offline': host.is_offline(),
            'cluster_nodes': host.cluster_nodes(),
        },
    )
