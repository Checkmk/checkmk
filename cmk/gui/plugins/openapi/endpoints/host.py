#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Hosts"""
import json

from cmk.gui import watolib
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.endpoints.folder import load_folder
from cmk.gui.plugins.openapi.restful_objects import constructors, response_schemas, endpoint_schema, \
    request_schemas
from cmk.gui.plugins.webapi import check_hostname, validate_host_attributes


@endpoint_schema('/collections/host',
                 method='post',
                 etag='output',
                 request_body_required=True,
                 request_schema=request_schemas.CreateHost,
                 response_schema=response_schemas.Host)
def create_host(params):
    """Create a host"""
    body = params['body']
    hostname = body['hostname']
    folder_id = body['folder']
    attributes = body.get('attributes', {})
    cluster_nodes = body.get('nodes', [])

    check_hostname(hostname, should_exist=False)
    for node in cluster_nodes:
        check_hostname(node, should_exist=True)

    validate_host_attributes(attributes, new=True)

    if folder_id == 'root':
        folder = watolib.Folder.root_folder()
    else:
        folder = load_folder(folder_id, status=400)

    folder.create_hosts([(hostname, attributes, cluster_nodes)])

    host = watolib.Host.host(hostname)
    return _serve_host(host)


@endpoint_schema('/objects/host/{hostname}',
                 method='put',
                 parameters=['hostname'],
                 etag='both',
                 request_body_required=True,
                 request_schema=request_schemas.UpdateHost,
                 response_schema=response_schemas.Host)
def update_host(params):
    """Update a host"""
    hostname = params['hostname']
    body = params['body']
    attributes = body['attributes']
    host = watolib.Host.host(hostname)  # type: watolib.CREHost
    constructors.require_etag(constructors.etag_of_obj(host))
    validate_host_attributes(attributes, new=False)
    host.update_attributes(attributes)
    return _serve_host(host)


@endpoint_schema('/objects/host/{hostname}',
                 method='delete',
                 parameters=['hostname'],
                 etag='input',
                 request_body_required=False,
                 output_empty=True)
def delete(params):
    """Delete a host"""
    hostname = params['hostname']
    check_hostname(hostname, should_exist=True)
    host = watolib.Host.host(hostname)
    constructors.require_etag(constructors.etag_of_obj(host))
    host.folder().delete_hosts([host.name()])
    return Response(status=204)


@endpoint_schema('/objects/host/{hostname}',
                 method='get',
                 parameters=['hostname'],
                 response_schema=response_schemas.Host)
def show_host(params):
    """Show a host"""
    hostname = params['hostname']
    host = watolib.Host.host(hostname)
    return _serve_host(host)


def _serve_host(host):
    response = Response()
    response.set_data(json.dumps(serialize_host(host)))
    response.set_content_type('application/json')
    response.headers.add('ETag', constructors.etag_of_obj(host).to_header())
    return response


def serialize_host(host):
    base = '/objects/host/%s' % (host.ident(),)
    return constructors.domain_object(
        domain_type='host',
        identifier=host.id(),
        title=host.alias(),
        members={
            'folder': constructors.object_property(
                name='folder',
                value=constructors.object_href('folder', host.folder()),
                prop_format='string',
                base=base,
            ),
        },
        extensions={},
    )
