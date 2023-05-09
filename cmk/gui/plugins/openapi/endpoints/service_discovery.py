#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Service discovery

A service discovery is the automatic and reliable detection of all services to be monitored on
a host.

You can find an introduction to services including service discovery in the
[Checkmk guide](https://docs.checkmk.com/latest/en/wato_services.html).
"""
import json
from typing import List, Optional

from cmk.gui import watolib
from cmk.gui.http import Response
from cmk.gui import fields
from cmk.gui.plugins.openapi.restful_objects import constructors, Endpoint, response_schemas
from cmk.gui.plugins.openapi.restful_objects.constructors import (
    collection_href,
    domain_object,
    link_rel,
    object_property,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import HOST_NAME
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.watolib.services import (
    checkbox_id,
    CheckTable,
    Discovery,
    DiscoveryAction,
    DiscoveryOptions,
    get_check_table,
    StartDiscoveryRequest,
)

SERVICE_DISCOVERY_PHASES = {
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

# param mode: can be one of "new", "remove", "fixall", "refresh", "only-host-labels"
DISCOVERY_ACTION = {
    "new": "new",
    "remove": "remove",
    "fix_all": "fixall",
    "refresh": "refresh",
    "only_host_labels": "only-host-labels",
}


@Endpoint(collection_href("service", "services"),
          '.../collection',
          method='get',
          response_schema=response_schemas.DomainObject,
          tag_group='Setup',
          query_params=[{
              'host_name': fields.HostField(
                  description='The host of the discovered services.',
                  example='example.com',
                  required=True,
              ),
              'discovery_phase': fields.String(
                  description='The discovery phase of the services.',
                  enum=sorted(SERVICE_DISCOVERY_PHASES.keys()),
                  example='monitored',
                  required=True,
              ),
          }])
def show_services(params):
    """Show all services of specific phase"""
    host = watolib.Host.load_host(params["host_name"])
    discovery_request = StartDiscoveryRequest(
        host=host,
        folder=host.folder(),
        options=DiscoveryOptions(
            action='',
            show_checkboxes=False,
            show_parameters=False,
            show_discovered_labels=False,
            show_plugin_names=False,
            ignore_errors=True,
        ),
    )
    discovery_result = get_check_table(discovery_request)
    return _serve_services(
        host,
        discovery_result.check_table,
        [params["discovery_phase"]],
    )


class UpdateDiscoveryPhase(BaseSchema):
    check_type = fields.String(
        description='The name of the check which this service uses.',
        example='df',
        required=True,
    )
    service_item = fields.String(
        description='The value uniquely identifying the service on a given host.',
        example='/home',
        required=True,
        allow_none=True,
    )
    target_phase = fields.String(
        description='The target phase of the service.',
        enum=sorted(SERVICE_DISCOVERY_PHASES.keys()),
        example='monitored',
        required=True,
    )


@Endpoint(constructors.object_action_href('host', '{host_name}', 'update_discovery_phase'),
          '.../modify',
          method='put',
          output_empty=True,
          tag_group='Setup',
          path_params=[{
              'host_name': fields.HostField(
                  description='The host of the service which shall be updated.',
                  example='example.com',
              ),
          }],
          status_descriptions={
              404: 'Host could not be found',
          },
          request_schema=UpdateDiscoveryPhase)
def update_service_phase(params):
    """Update the phase of a service"""
    body = params['body']
    host = watolib.Host.load_host(params["host_name"])
    target_phase = body["target_phase"]
    check_type = body['check_type']
    service_item = body['service_item']
    _update_single_service_phase(
        SERVICE_DISCOVERY_PHASES[target_phase],
        host,
        check_type,
        service_item,
    )
    return Response(status=204)


def _update_single_service_phase(
    target_phase: str,
    host: watolib.CREHost,
    check_type: str,
    service_item: Optional[str],
) -> None:
    discovery = Discovery(
        host=host,
        discovery_options=DiscoveryOptions(
            action=DiscoveryAction.SINGLE_UPDATE,
            show_checkboxes=False,
            show_parameters=False,
            show_discovered_labels=False,
            show_plugin_names=False,
            ignore_errors=True,
        ),
        request={
            "update_target": target_phase,
            "update_services": [checkbox_id(
                check_type,
                service_item,
            )]
        },
    )
    discovery.execute_discovery()


class DiscoverServices(BaseSchema):
    mode = fields.String(
        description='''The mode of the discovery action. Can be one of:

 * `new` - Add unmonitored services and new host labels
 * `remove` - Remove vanished services
 * `fix_all` - Add unmonitored services and new host labels, remove vanished services
 * `refresh` - Refresh all services (tabula rasa), add new host labels
 * `only_host_labels` - Only discover new host labels
''',
        enum=list(DISCOVERY_ACTION.keys()),
        example='refresh',
        missing='fix_all',
    )


@Endpoint(
    constructors.object_action_href('host', '{host_name}', 'discover_services'),
    '.../update',
    method='post',
    tag_group='Setup',
    status_descriptions={
        404: 'Host could not be found',
    },
    path_params=[HOST_NAME],
    request_schema=DiscoverServices,
    response_schema=response_schemas.DomainObject,
)
def execute(params):
    """Execute a service discovery on a host"""
    host = watolib.Host.load_host(params["host_name"])
    body = params['body']
    discovery_request = StartDiscoveryRequest(
        host=host,
        folder=host.folder(),
        options=DiscoveryOptions(
            action=DISCOVERY_ACTION[body["mode"]],
            show_checkboxes=False,
            show_parameters=False,
            show_discovered_labels=False,
            show_plugin_names=False,
            ignore_errors=True,
        ),
    )
    discovery_result = get_check_table(discovery_request)
    return _serve_services(
        host,
        discovery_result.check_table,
        list(SERVICE_DISCOVERY_PHASES.keys()),
    )


def _serve_services(
    host: watolib.CREHost,
    discovered_services: CheckTable,
    discovery_phases: List[str],
):
    response = Response()
    response.set_data(
        json.dumps(serialize_service_discovery(host, discovered_services, discovery_phases)))

    response.set_content_type('application/json')
    return response


def _in_phase(phase_to_check: str, discovery_phases: List[str]) -> bool:
    for phase in list(discovery_phases):
        if SERVICE_DISCOVERY_PHASES[phase] == phase_to_check:
            return True
    return False


def _lookup_phase_name(internal_phase_name: str) -> str:
    for key, value in SERVICE_DISCOVERY_PHASES.items():
        if value == internal_phase_name:
            return key
    raise ValueError(f"Key {internal_phase_name} not found in dict.")


def serialize_service_discovery(
    host: watolib.CREHost,
    discovered_services: CheckTable,
    discovery_phases: List[str],
):

    members = {}
    host_name = host.name()
    for entry in discovered_services:
        (table_source, check_type, _checkgroup, item, _discovered_params, _check_params, descr,
         _service_phase, _output, _perfdata, _service_labels, _found_on_nodes) = entry
        if _in_phase(table_source, discovery_phases):
            service_phase = _lookup_phase_name(table_source)
            members[f"{check_type}-{item}"] = object_property(
                name=descr,
                title=f"The service is currently {service_phase!r}",
                value=service_phase,
                prop_format='string',
                linkable=False,
                extensions={
                    "host_name": host_name,
                    "check_plugin_name": check_type,
                    "service_name": descr,
                    "service_item": item,
                    "service_phase": service_phase,
                },
                base='',
                links=[
                    link_rel(
                        rel="cmk/service.move-monitored",
                        href=update_service_phase.path.format(host_name=host_name),
                        body_params={
                            'target_phase': 'monitored',
                            'check_type': check_type,
                            'service_item': item,
                        },
                        method='put',
                        title='Move the service to monitored',
                    ),
                    link_rel(
                        rel="cmk/service.move-undecided",
                        href=update_service_phase.path.format(host_name=host_name),
                        body_params={
                            'target_phase': 'undecided',
                            'check_type': check_type,
                            'service_item': item,
                        },
                        method='put',
                        title='Move the service to undecided',
                    ),
                    link_rel(
                        rel="cmk/service.move-ignored",
                        href=update_service_phase.path.format(host_name=host_name),
                        body_params={
                            'target_phase': 'ignored',
                            'check_type': check_type,
                            'service_item': item,
                        },
                        method='put',
                        title='Move the service to ignored',
                    ),
                ],
            )

    return domain_object(
        domain_type='service_discovery',
        identifier=f'{host_name}-services-wato',
        title='Services discovery',
        members=members,
        editable=False,
        deletable=False,
        extensions={},
    )
