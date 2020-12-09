#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Acknowledge problems

A problem occurs if a host is not UP or a service ist not OK.
The acknowledgement of the problem is the indication that the reported issue is known and that
somebody is attending to it.

You can find an introduction to the acknowledgement of problems in the
[Checkmk guide](https://checkmk.com/cms_basics_ackn.html).
"""
# TODO: List acknowledgments
# TODO: Acknowledge service problem
from urllib.parse import unquote

from cmk.gui import config, sites, http
from cmk.gui.plugins.openapi import fields
from cmk.gui.plugins.openapi.livestatus_helpers.commands.acknowledgments import (
    acknowledge_host_problem,
    acknowledge_hostgroup_problem,
    acknowledge_service_problem,
    acknowledge_servicegroup_problem,
)
from cmk.gui.plugins.openapi.livestatus_helpers.expressions import And, Or, tree_to_expr
from cmk.gui.plugins.openapi.livestatus_helpers.queries import Query
from cmk.gui.plugins.openapi.livestatus_helpers.tables import Hosts, Services
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    request_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import HOST_NAME
from cmk.gui.plugins.openapi.utils import problem

SERVICE_DESCRIPTION = {
    'service_description': fields.String(
        description="The service description.",
        example="Memory",
    )
}


@Endpoint(constructors.collection_href('acknowledge', 'host'),
          'cmk/create',
          method='post',
          tag_group='Monitoring',
          request_schema=request_schemas.AcknowledgeHostRelatedProblem,
          output_empty=True)
def set_acknowledgement_related_to_host(params):
    """Set acknowledgement on related hosts"""
    body = params['body']
    live = sites.live()

    sticky = body['sticky']
    notify = body['notify']
    persistent = body['persistent']
    comment = body['comment']

    acknowledge_type = body['acknowledge_type']

    if acknowledge_type == 'host':
        return _set_acknowledgement_on_host(
            live,
            body['host_name'],
            sticky,
            notify,
            persistent,
            comment,
        )

    if acknowledge_type == 'hostgroup':
        return _set_acknowledgement_on_hostgroup(
            live,
            body['hostgroup_name'],
            sticky,
            notify,
            persistent,
            comment,
        )

    if acknowledge_type == 'host_by_query':
        return _set_acknowlegement_on_queried_hosts(
            live,
            body['query'],
            sticky,
            notify,
            persistent,
            comment,
        )

    return problem(status=400,
                   title="Unhandled acknowledge-type.",
                   detail=f"The acknowledge-type {acknowledge_type!r} is not supported.")


def _set_acknowledgement_on_host(
    connection,
    host_name: str,
    sticky: bool,
    notify: bool,
    persistent: bool,
    comment: str,
):
    """Acknowledge for a specific host"""
    host = Query([Hosts.name, Hosts.state], Hosts.name.equals(host_name)).first(connection)
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
        sticky=sticky,
        notify=notify,
        persistent=persistent,
        user=_user_id(),
        comment=comment,
    )
    return http.Response(status=204)


def _set_acknowlegement_on_queried_hosts(
    connection,
    query: str,
    sticky: bool,
    notify: bool,
    persistent: bool,
    comment: str,
):
    q = Query([Hosts.name, Hosts.state]).filter(tree_to_expr(query))
    hosts = list(q.iterate(connection))

    if not hosts:
        return problem(status=404, title="The provided query returned no monitored hosts")

    for host in hosts:
        if host.state == 0:
            continue
        acknowledge_host_problem(
            connection,
            host.name,
            sticky=sticky,
            notify=notify,
            persistent=persistent,
            user=_user_id(),
            comment=comment,
        )

    return http.Response(status=204)


def _set_acknowledgement_on_hostgroup(
    connection,
    hostgroup_name: str,
    sticky: bool,
    notify: bool,
    persistent: bool,
    comment: str,
):
    """Acknowledge for hosts of a host group"""
    acknowledge_hostgroup_problem(
        connection,
        hostgroup_name,
        sticky=sticky,
        notify=notify,
        persistent=persistent,
        user=_user_id(),
        comment=comment,
    )
    return http.Response(status=204)


@Endpoint(constructors.collection_href('acknowledge', 'service'),
          'cmk/create_service',
          method='post',
          tag_group='Monitoring',
          request_schema=request_schemas.AcknowledgeServiceRelatedProblem,
          output_empty=True)
def set_acknowledgement_on_service_related(params):
    """Acknowledge for related service"""
    body = params['body']
    live = sites.live()

    sticky = body['sticky']
    notify = body['notify']
    persistent = body['persistent']
    comment = body['comment']

    acknowledge_type = body['acknowledge_type']

    if acknowledge_type == 'service':
        return _set_acknowledgement_for_service(
            live,
            unquote(body['service_description']),
            sticky,
            notify,
            persistent,
            comment,
        )

    if acknowledge_type == 'servicegroup':
        acknowledge_servicegroup_problem(
            live,
            body['servicegroup_name'],
            sticky=sticky,
            notify=notify,
            persistent=persistent,
            user=_user_id(),
            comment=comment,
        )
        return http.Response(status=204)

    return problem(status=400,
                   title="Unhandled acknowledge-type.",
                   detail=f"The acknowledge-type {acknowledge_type!r} is not supported.")


def _set_acknowledgement_for_service(
    connection,
    service_description: str,
    sticky: bool,
    notify: bool,
    persistent: bool,
    comment: str,
):
    q = Query([Services.host_name, Services.description, Services.state]).filter(
        tree_to_expr({
            'op': '=',
            'left': 'services.description',
            'right': service_description
        }))
    services = list(q.iterate(connection))

    if not len(services):
        return problem(
            status=404,
            title=f'No services with {service_description!r} were found.',
        )

    for service in services:
        if service.state == 0:
            continue
        acknowledge_service_problem(
            connection,
            service.host_name,
            service.description,
            sticky=sticky,
            notify=notify,
            persistent=persistent,
            user=_user_id(),
            comment=comment,
        )

    return http.Response(status=204)


@Endpoint(
    "/objects/host/{host_name}/objects/service/{service_description}/actions/acknowledge/invoke",
    'cmk/create',
    method='post',
    tag_group='Monitoring',
    path_params=[
        HOST_NAME,
        SERVICE_DESCRIPTION,
    ],
    request_schema=request_schemas.AcknowledgeServiceProblem,
    output_empty=True)
def set_acknowledgement_on_host_service(params):
    """Acknowledge for services on a host"""
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


@Endpoint(constructors.domain_type_action_href("service", "bulk-acknowledge"),
          'cmk/service.bulk-acknowledge',
          method='post',
          tag_group='Monitoring',
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


# mypy can't know this will work.
def _user_id() -> str:
    if config.user.id is None:
        raise RuntimeError("No user set. Check your setup.")
    return config.user.id
