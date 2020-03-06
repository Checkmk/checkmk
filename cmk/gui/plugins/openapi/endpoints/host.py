#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from connexion import ProblemException  # type: ignore
from werkzeug.datastructures import ETags

from cmk.gui import watolib
from cmk.gui.globals import response
from cmk.gui.plugins.openapi.endpoints.folder import load_folder
from cmk.gui.plugins.openapi.restful_objects import constructors, response_schemas, endpoint_schema
from cmk.gui.plugins.webapi import check_hostname, validate_host_attributes


@endpoint_schema('/collections/host',
                 method='post',
                 etag='output',
                 request_body_required=True,
                 request_schema=response_schemas.InputHost,
                 response_schema=response_schemas.Host)
def create(params):
    body = params['body']
    hostname = body['hostname']
    folder_id = body['folder']
    attributes = body.get('attributes', {})
    cluster_nodes = None

    check_hostname(hostname, should_exist=False)
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
                 request_schema=response_schemas.InputHost,
                 response_schema=response_schemas.Host)
def update(params):
    hostname = params['hostname']
    body = params['body']
    attributes = body['attributes']
    host = watolib.Host.host(hostname)  # type: watolib.Host
    host.update_attributes(attributes)
    return _serve_host(host)


@endpoint_schema('/objects/host/{hostname}',
                 method='delete',
                 parameters=['hostname'],
                 etag='input',
                 request_body_required=False,
                 output_empty=True)
def delete(params):
    hostname = params['hostname']
    check_hostname(hostname, should_exist=True)

    host = watolib.Host.host(hostname)
    host.folder().delete_hosts([host.name()])
    return constructors.sucess(status=204)


@endpoint_schema('/objects/host/{hostname}',
                 method='get',
                 parameters=['hostname'],
                 response_schema=response_schemas.Host)
def get(params):
    hostname = params['hostname']
    host = watolib.Host.host(hostname)
    return _serve_host(host)


def _serve_host(host):
    response.set_data(json.dumps(serialize_host(host)))
    response.set_content_type('application/json')
    response.headers.add('ETag', _get_etag(host).to_header())
    return response._get_current_object()


def _get_etag(folder):
    attributes = folder.attributes()
    if 'meta_data' in attributes:
        etags = [str(attributes['meta_data']['updated_at'])]
        return ETags(strong_etags=etags)
    else:
        raise ProblemException(500, "Folder %r has no meta_data." % (folder.name(),),
                               "Can't create ETag.")


def serialize_host(host):
    base = '/objects/host/%s' % (host.ident(),)
    return constructors.domain_object(
        domain_type='host',
        identifier=host.id(),
        title=host.alias(),
        members=dict([
            constructors.object_property_member(
                'folder',
                constructors.object_href('folder', host.folder()),
                base,
            ),
        ]),
        extensions={},
    )
