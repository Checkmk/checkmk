#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Service discovery

A service discovery is the automatic and reliable detection of all services to be monitored on
a host.

You can find an introduction to services including service discovery in the
[Checkmk guide](https://checkmk.com/cms_wato_services.html).
"""
import json

from cmk.gui import watolib
from cmk.gui.plugins.openapi import fields
from cmk.gui.plugins.openapi.restful_objects.parameters import HOST_NAME
from cmk.gui.watolib.services import (
    Discovery,
    StartDiscoveryRequest,
    DiscoveryOptions,
    get_check_table,
    checkbox_id,
)
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.restful_objects import (
    Endpoint,
    response_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.constructors import (domain_object, object_property,
                                                                  link_rel, collection_href)

SERVICE_DISCOVERY_STATES = {
    "undecided": "new",
    "vanished": "vanished",
    "monitored": "old",
    "ignored": "ignored",
    "removed": "removed",
    "manual": "manual",
    "active": "active",
    "custom": "custom",
    "clustered_monitored": "clustered_old",
    "clustered_undecided": "clustered_new",
    "clustered_vanished": "clustered_vanished",
    "clustered_ignored": "clustered_ignored",
    "active_ignored": "active_ignored",
    "custom_ignored": "custom_ignored",
    "legacy": "legacy",
    "legacy_ignored": "legacy_ignored"
}

DISCOVERY_ACTION = {"tabula-rasa": "refresh"}


@Endpoint(
    collection_href("service", "services"),
    '.../collection',
    method='get',
    response_schema=response_schemas.DomainObject,
    tag_group='Setup',
    query_params=[{
        'host_name': fields.String(
            pattern="[a-zA-Z][a-zA-Z0-9_-]+",
            description=('Optionally the hostname for which a certain agent has '
                         'been configured. If omitted you may only download this agent if you '
                         'have the rights for all agents.'),
            example='example.com',
            required=True,
        ),
        'discovery_state': fields.String(
            description=('The discovery state of the services. May be one of the following: ' +
                         ', '.join(sorted(SERVICE_DISCOVERY_STATES.keys()))),
            pattern='|'.join(sorted(SERVICE_DISCOVERY_STATES.keys())),
            example='monitored',
            required=True,
        )
    }])
def show_services(params):
    """Show all services of specific state"""
    host = watolib.Host.host(params["host_name"])
    discovery_request = StartDiscoveryRequest(
        host=host,
        folder=host.folder(),
        options=DiscoveryOptions(action='',
                                 show_checkboxes=False,
                                 show_parameters=False,
                                 show_discovered_labels=False,
                                 show_plugin_names=False,
                                 ignore_errors=True),
    )
    discovery_result = get_check_table(discovery_request)
    return _serve_services(host, discovery_result.check_table, params["discovery_state"])


@Endpoint(
    '/objects/host/{host_name}/service/{service_hash}/action/move/{target_state}',
    '.../modify',
    method='put',
    output_empty=True,
    tag_group='Setup',
    path_params=[{
        "service_hash": fields.String(
            description='A name used as an identifier. Can be of arbitrary length',
            pattern="[a-zA-Z][a-zA-Z0-9_-]+",
            example='asoidjfo2jifa09',
            required=True,
        ),
        'target_state': fields.String(
            description=('The discovery state of the services. May be one of the following: ' +
                         ', '.join(sorted(SERVICE_DISCOVERY_STATES.keys()))),
            pattern='|'.join(sorted(SERVICE_DISCOVERY_STATES.keys())),
            example='monitored',
            required=True,
        ),
        **HOST_NAME,
    }])
def move_service(params):
    """Update the phase of a service"""
    host = watolib.Host.host(params["host_name"])
    discovery_request = {
        "update_target": params["target_state"],
        "update_services": [params["service_hash"]]
    }

    discovery_options = DiscoveryOptions(action='single-update',
                                         show_checkboxes=False,
                                         show_parameters=False,
                                         show_discovered_labels=False,
                                         show_plugin_names=False,
                                         ignore_errors=True)

    discovery = Discovery(host=host, discovery_options=discovery_options, request=discovery_request)

    discovery.execute_discovery()
    return Response(status=204)


@Endpoint('/objects/host/{host_name}/actions/discover-services/mode/{discover_mode}',
          '.../update',
          method='post',
          output_empty=True,
          tag_group='Setup',
          path_params=[{
              'discover_mode': fields.String(
                  description=('The mode of the discovery action. May be one of the following: ' +
                               ', '.join(sorted(DISCOVERY_ACTION.keys()))),
                  pattern='|'.join(sorted(DISCOVERY_ACTION.keys())),
                  example='tabula-rasa',
                  required=True,
              ),
              **HOST_NAME,
          }])
def execute(params):
    """Execute a service discovery on a host"""
    host = watolib.Host.host(params["host_name"])
    discovery_request = StartDiscoveryRequest(host=host,
                                              folder=host.folder(),
                                              options=DiscoveryOptions(
                                                  action=DISCOVERY_ACTION[params["discover_mode"]],
                                                  show_checkboxes=False,
                                                  show_parameters=False,
                                                  show_discovered_labels=False,
                                                  show_plugin_names=False,
                                                  ignore_errors=True))
    _discovery_result = get_check_table(discovery_request)
    return Response(status=204)


def _serve_services(host, discovered_services, discovery_state):
    response = Response()
    response.set_data(
        json.dumps(serialize_service_discovery(host, discovered_services, discovery_state)))
    response.set_content_type('application/json')
    return response


SERVICE_STATE = {0: "OK", 1: "WARN", 2: "CRIT"}


def serialize_service_discovery(host, discovered_services, discovery_state):
    members = {}
    for (table_source, check_type, _checkgroup, item, _discovered_params, _check_params, descr,
         _service_state, _output, _perfdata, _service_labels,
         _found_on_nodes) in discovered_services:

        if table_source == SERVICE_DISCOVERY_STATES[discovery_state]:
            service_hash = checkbox_id(check_type, item)
            members[service_hash] = {
                "service_name": descr,
                "check_plugin_name": check_type,
                "state": object_property(
                    name=descr,
                    title="The service is currently %s" % discovery_state,
                    value=table_source,
                    prop_format='string',
                    base='',
                    links=[
                        link_rel(rel="cmk/service.move-monitored",
                                 href="/objects/host/%s/service/%s/action/move/monitored" %
                                 (host.ident(), service_hash),
                                 method='put',
                                 title='Move the service to monitored'),
                        link_rel(rel="cmk/service.move-undecided",
                                 href="/objects/host/%s/service/%s/action/move/undecided" %
                                 (host.ident(), service_hash),
                                 method='put',
                                 title='Move the service to undecided'),
                        link_rel(rel="cmk/service.move-ignored",
                                 href="/objects/host/%s/service/%s/action/move/ignored" %
                                 (host.ident(), service_hash),
                                 method='put',
                                 title='Move the service to ignored'),
                    ]),
            }

    return domain_object(
        domain_type='service_discovery',
        identifier='%s-services-%s' % (host.ident(), "wato"),
        title='Services discovery',
        members=members,
        extensions={},
    )
