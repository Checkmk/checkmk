#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Acknowledge problems"""

# TODO: List acknowledgments
# TODO: Acknowledge service problem
from urllib.parse import unquote

from connexion import problem  # type: ignore[import]

from cmk.gui import config, sites, http
from cmk.gui.plugins.openapi.livestatus_helpers.commands.acknowledgments import \
    acknowledge_host_problem, acknowledge_service_problem
from cmk.gui.plugins.openapi.livestatus_helpers.expressions import And
from cmk.gui.plugins.openapi.livestatus_helpers.queries import Query
from cmk.gui.plugins.openapi.livestatus_helpers.tables import Hosts, Services
from cmk.gui.plugins.openapi.restful_objects import constructors, endpoint_schema, request_schemas


@endpoint_schema(constructors.object_action_href('host', '{host_name}', 'acknowledge'),
                 'cmk/create',
                 method='post',
                 parameters=[
                     'host_name',
                 ],
                 request_schema=request_schemas.AcknowledgeHostProblem,
                 output_empty=True)
def set_acknowledgement_on_host(params):
    """Acknowledge problems on a specific host."""
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
        sticky=params.get('sticky'),
        notify=params.get('notify'),
        persistent=params.get('persistent'),
        user=str(config.user.id),
        comment=params.get('comment', 'Acknowledged'),
    )
    return http.Response(status=204)


#
# Acknowledge all services of a given name:
#    /objects/service/service_description/actions/acknowledge
#


@endpoint_schema(
    "/objects/host/{host_name}/objects/service/{service_description}/actions/acknowledge",
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
        user=str(config.user.id),
        comment=body.get('comment', 'Acknowledged'),
    )
    return http.Response(status=204)
