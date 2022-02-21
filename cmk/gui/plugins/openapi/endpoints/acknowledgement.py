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
[Checkmk guide](https://docs.checkmk.com/latest/en/basics_ackn.html).
"""
# TODO: List acknowledgments
from urllib.parse import unquote

from cmk.gui import config, fields, sites, http
from cmk.gui.livestatus_utils.commands.acknowledgments import (
    acknowledge_host_problem,
    acknowledge_hostgroup_problem,
    acknowledge_service_problem,
    acknowledge_servicegroup_problem,
)
from cmk.utils.livestatus_helpers.expressions import And
from cmk.utils.livestatus_helpers.queries import Query
from cmk.utils.livestatus_helpers.tables import Hosts, Services
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    request_schemas,
)
from cmk.gui.plugins.openapi.utils import ProblemException

SERVICE_DESCRIPTION = {
    'service_description': fields.String(
        description="The service description.",
        example="Memory",
    )
}


@Endpoint(
    constructors.collection_href('acknowledge', 'host'),
    'cmk/create',
    method='post',
    tag_group='Monitoring',
    skip_locking=True,
    additional_status_codes=[422],
    status_descriptions={
        422: 'The query yielded no result.',
    },
    request_schema=request_schemas.AcknowledgeHostRelatedProblem,
    output_empty=True,
    update_config_generation=False,
)
def set_acknowledgement_on_hosts(params):
    """Set acknowledgement on related hosts"""
    body = params['body']
    live = sites.live()

    sticky = body['sticky']
    notify = body['notify']
    persistent = body['persistent']
    comment = body['comment']

    acknowledge_type = body['acknowledge_type']

    if acknowledge_type == 'host':
        name = body['host_name']
        host_state = Query([Hosts.state], Hosts.name == name).value(live)
        if not host_state:
            raise ProblemException(
                status=422,
                title=f'Host {name!r} has no problem.',
            )
        acknowledge_host_problem(
            live,
            name,
            sticky=sticky,
            notify=notify,
            persistent=persistent,
            user=config.user.ident,
            comment=comment,
        )
    elif acknowledge_type == 'hostgroup':
        host_group = body['hostgroup_name']
        try:
            acknowledge_hostgroup_problem(
                live,
                host_group,
                sticky=sticky,
                notify=notify,
                persistent=persistent,
                user=config.user.ident,
                comment=comment,
            )
        except ValueError:
            raise ProblemException(
                400,
                title="Hostgroup could not be found.",
                detail=f"Unknown hostgroup: {host_group}",
            )
    elif acknowledge_type == 'host_by_query':
        query = body['query']
        hosts = Query([Hosts.name], query).fetchall(live)
        if not hosts:
            raise ProblemException(
                status=422,
                title="The provided query returned no monitored hosts",
            )
        for host in hosts:
            acknowledge_host_problem(
                live,
                host.name,
                sticky=sticky,
                notify=notify,
                persistent=persistent,
                user=config.user.ident,
                comment=comment,
            )
    else:
        raise ProblemException(
            status=400,
            title="Unhandled acknowledge-type.",
            detail=f"The acknowledge-type {acknowledge_type!r} is not supported.",
        )

    return http.Response(status=204)


@Endpoint(
    constructors.collection_href('acknowledge', 'service'),
    'cmk/create_service',
    method='post',
    tag_group='Monitoring',
    skip_locking=True,
    additional_status_codes=[422],
    status_descriptions={
        422: 'Service was not in a problem state.',
    },
    request_schema=request_schemas.AcknowledgeServiceRelatedProblem,
    output_empty=True,
    update_config_generation=False,
)
def set_acknowledgement_on_services(params):
    """Set acknowledgement on related services"""
    body = params['body']
    live = sites.live()

    sticky = body['sticky']
    notify = body['notify']
    persistent = body['persistent']
    comment = body['comment']
    acknowledge_type = body['acknowledge_type']

    if acknowledge_type == 'service':
        description = unquote(body['service_description'])
        host_name = body['host_name']
        service = Query([Services.host_name, Services.description, Services.state],
                        And(Services.host_name == host_name,
                            Services.description == description)).first(live)
        if not service:
            raise ProblemException(
                status=400,
                title=f'Service {description!r}@{host_name!r} could not be found.',
            )
        if not service.state:
            raise ProblemException(
                status=422,
                title=f'Service {description!r}@{host_name!r} has no problem.',
            )
        acknowledge_service_problem(
            live,
            service.host_name,
            service.description,
            sticky=sticky,
            notify=notify,
            persistent=persistent,
            user=config.user.ident,
            comment=comment,
        )
    elif acknowledge_type == 'servicegroup':
        service_group = body['servicegroup_name']
        try:
            acknowledge_servicegroup_problem(
                live,
                service_group,
                sticky=sticky,
                notify=notify,
                persistent=persistent,
                user=config.user.ident,
                comment=comment,
            )
        except ValueError:
            raise ProblemException(
                status=400,
                title="Servicegroup could not be found.",
                detail=f"Unknown servicegroup: {service_group}",
            )
    elif acknowledge_type == 'service_by_query':
        services = Query(
            [Services.host_name, Services.description, Services.state],
            body['query'],
        ).fetchall(live)
        if not services:
            raise ProblemException(
                status=422,
                title='No services with problems found.',
                detail='All queried services are OK.',
            )

        for service in services:
            if not service.state:
                continue
            acknowledge_service_problem(
                live,
                service.host_name,
                service.description,
                sticky=sticky,
                notify=notify,
                persistent=persistent,
                user=config.user.ident,
                comment=comment,
            )
    else:
        raise ProblemException(
            status=400,
            title="Unhandled acknowledge-type.",
            detail=f"The acknowledge-type {acknowledge_type!r} is not supported.",
        )

    return http.Response(status=204)
