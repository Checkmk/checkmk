#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Acknowledge problems"""

# TODO: List acknowledgments
# TODO: Acknowledge service problem
from urllib.parse import unquote
from typing import Dict

from connexion import problem  # type: ignore[import]

from cmk.gui import config, sites, http
from cmk.gui.plugins.openapi.livestatus_helpers.commands.acknowledgments import (
    acknowledge_host_problem,
    acknowledge_hostgroup_problem,
    acknowledge_service_problem,
    acknowledge_servicegroup_problem,
)
from cmk.gui.plugins.openapi.livestatus_helpers.expressions import And, Or
from cmk.gui.plugins.openapi.livestatus_helpers.queries import Query
from cmk.gui.plugins.openapi.livestatus_helpers.tables import Hosts, Services
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    endpoint_schema,
    request_schemas,
    ParamDict,
)


@endpoint_schema(constructors.object_action_href('host', '{host_name}', 'acknowledge'),
                 'cmk/create',
                 method='post',
                 parameters=[
                     'host_name',
                 ],
                 request_schema=request_schemas.AcknowledgeHostProblem,
                 output_empty=True)
def set_acknowledgement_on_host(params):
    """Acknowledge problems on a specific host"""
    host_name = params['host_name']

    host = Query([Hosts.name, Hosts.state], Hosts.name.equals(host_name)).first(sites.live())
    if host is None:
        return problem(
            status=404,
            title=f'Host {host_name} does not exist.',
            detail='It is not currently monitored.',
        )

    if host.state == 0:
        return problem(status=400,
                       title=f"Host {host_name} does not have a problem.",
                       detail="The state is UP.")

    acknowledge_host_problem(
        sites.live(),
        host_name,
        sticky=bool(params.get('sticky')),
        notify=bool(params.get('notify')),
        persistent=bool(params.get('persistent')),
        user=_user_id(),
        comment=params.get('comment', 'Acknowledged'),
    )
    return http.Response(status=204)


@endpoint_schema(constructors.object_action_href('hostgroup', '{hostgroup_name}', 'acknowledge'),
                 'cmk/create',
                 method='post',
                 parameters=[
                     ParamDict.create('hostgroup_name',
                                      'path',
                                      description='The name of the host group',
                                      example='samples',
                                      required=True),
                 ],
                 request_schema=request_schemas.AcknowledgeHostProblem,
                 output_empty=True)
def set_acknowledgement_on_hostgroup(params):
    """Acknowledge problems for hosts of a host group"""
    body = params['body']
    acknowledge_hostgroup_problem(
        sites.live(),
        params['hostgroup_name'],
        sticky=body['sticky'],
        notify=body['notify'],
        persistent=body['persistent'],
        user=config.user.ident,
        comment=body['comment'],
    )
    return http.Response(status=204)


@endpoint_schema(constructors.domain_type_action_href('host', 'bulk-acknowledge'),
                 'cmk/create',
                 method='post',
                 request_schema=request_schemas.BulkAcknowledgeHostProblem,
                 output_empty=True)
def bulk_set_acknowledgement_on_hosts(params):
    """Bulk acknowledge on selected hosts"""
    live = sites.live()
    entries = params['entries']

    hosts: Dict[str, int] = {
        host_name: host_state for host_name, host_state in Query(  # pylint: disable=unnecessary-comprehension
            [Hosts.name, Hosts.state],
            And(*[Hosts.name.equals(host_name) for host_name in entries]),
        ).fetch_values(live)
    }

    not_found = []
    for host_name in entries:
        if host_name not in hosts:
            not_found.append(host_name)

    if not_found:
        return problem(status=400,
                       title=f"Hosts {', '.join(not_found)} not found",
                       detail='Current not monitored')

    up_hosts = []
    for host_name in entries:
        if hosts[host_name] == 0:
            up_hosts.append(host_name)

    if up_hosts:
        return problem(status=400,
                       title=f"Hosts {', '.join(up_hosts)} do not have a problem",
                       detail="The states of these hosts are UP")

    for host_name in entries:
        acknowledge_host_problem(
            sites.live(),
            host_name,
            sticky=params.get('sticky'),
            notify=params.get('notify'),
            persistent=params.get('persistent'),
            user=_user_id(),
            comment=params.get('comment', 'Acknowledged'),
        )
    return http.Response(status=204)


@endpoint_schema("/domain-types/service/{service_description}/actions/acknowledge/invoke",
                 'cmk/create',
                 method='post',
                 parameters=['service_description'],
                 request_schema=request_schemas.AcknowledgeServiceProblem,
                 output_empty=True)
def set_acknowledgement_for_service(params):
    """Acknowledge problems for a specific service globally"""
    service_description = unquote(params['service_description'])
    body = params['body']

    live = sites.live()

    services = Query(
        [Services.host_name, Services.description],
        And(
            Services.description.equals(service_description),
            Or(
                Services.state == 1,
                Services.state == 2,
            ),
        ),
    ).fetch_values(live)

    if not len(services):
        return problem(
            status=400,
            title=f'No services {service_description!r} with problems found.',
            detail='All services are OK.',
        )

    for _host_name, _service_description in services:
        acknowledge_service_problem(
            live,
            _host_name,
            _service_description,
            sticky=body.get('sticky', False),
            notify=body.get('notify', False),
            persistent=body.get('persistent', False),
            user=_user_id(),
            comment=body.get('comment', 'Acknowledged'),
        )

    return http.Response(status=204)


@endpoint_schema(
    "/objects/host/{host_name}/objects/service/{service_description}/actions/acknowledge/invoke",
    'cmk/create',
    method='post',
    parameters=['host_name', 'service_description'],
    request_schema=request_schemas.AcknowledgeServiceProblem,
    output_empty=True)
def set_acknowledgement_on_host_service(params):
    """Acknowledge problems of a specific service on a specific host"""
    host_name = params['host_name']
    service_description = unquote(params['service_description'])
    body = params['body']

    service = Query([Services.description, Services.state],
                    And(Services.description.equals(service_description),
                        Services.host_name.equals(host_name))).first(sites.live())

    if service is None:
        return problem(
            status=404,
            title=f'Service {service_description!r} on host {host_name!r} does not exist.',
            detail='It is not currently monitored.',
        )

    if service.state == 0:
        return problem(status=400,
                       title=f"Service {service_description!r} does not have a problem.",
                       detail="The state is OK.")

    acknowledge_service_problem(
        sites.live(),
        host_name,
        service_description,
        sticky=body.get('sticky', False),
        notify=body.get('notify', False),
        persistent=body.get('persistent', False),
        user=_user_id(),
        comment=body.get('comment', 'Acknowledged'),
    )
    return http.Response(status=204)


@endpoint_schema(constructors.domain_type_action_href("service", "bulk-acknowledge"),
                 'cmk/service.bulk-acknowledge',
                 method='post',
                 request_schema=request_schemas.BulkAcknowledgeServiceProblem,
                 output_empty=True)
def bulk_set_acknowledgement_on_host_service(params):
    """Bulk Acknowledge specific services on specific host"""
    live = sites.live()
    body = params['body']
    host_name = body['host_name']
    entries = body.get('entries', [])

    query = Query(
        [Services.description, Services.state],
        And(
            Services.host_name.equals(host_name),
            Or(*[
                Services.description.equals(service_description) for service_description in entries
            ])))

    services = query.to_dict(live)

    not_found = []
    for service_description in entries:
        if service_description not in services:
            not_found.append(service_description)

    if not_found:
        return problem(status=400,
                       title=f"Services {', '.join(not_found)} not found on host {host_name}",
                       detail='Currently not monitored')

    up_services = []
    for service_description in entries:
        if services[service_description] == 0:
            up_services.append(service_description)

    if up_services:
        return problem(status=400,
                       title=f"Services {', '.join(up_services)} do not have a problem",
                       detail="The states of these services are OK")

    for service_description in entries:
        acknowledge_service_problem(
            sites.live(),
            host_name,
            service_description,
            sticky=body.get('sticky', False),
            notify=body.get('notify', False),
            persistent=body.get('persistent', False),
            user=str(config.user.id),
            comment=body.get('comment', 'Acknowledged'),
        )
    return http.Response(status=204)


@endpoint_schema(constructors.object_action_href('servicegroup', '{servicegroup_name}',
                                                 'acknowledge'),
                 'cmk/create',
                 method='post',
                 parameters=[
                     ParamDict.create('servicegroup_name',
                                      'path',
                                      description='The name of the service group',
                                      example='windows',
                                      required=True),
                 ],
                 request_schema=request_schemas.AcknowledgeServiceProblem,
                 output_empty=True)
def set_acknowledgement_on_servicegroup(params):
    """Acknowledge problems for services of a service group"""
    body = params['body']
    acknowledge_servicegroup_problem(
        sites.live(),
        params['servicegroup_name'],
        sticky=body['sticky'],
        notify=body['notify'],
        persistent=body['persistent'],
        user=config.user.ident,
        comment=body['comment'],
    )
    return http.Response(status=204)


# mypy can't know this will work.
def _user_id() -> str:
    if config.user.id is None:
        raise RuntimeError("No user set. Check your setup.")
    return config.user.id
