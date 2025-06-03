#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Acknowledge problems

A problem occurs if a host is not UP or a service ist not OK.
The acknowledgement of the problem is the indication that the reported issue is known and that
somebody is attending to it.

You can find an introduction to the acknowledgement of problems in the
[Checkmk guide](https://docs.checkmk.com/latest/en/basics_ackn.html).
"""

from collections.abc import Mapping

# TODO: List acknowledgments
from typing import Any
from urllib.parse import unquote

from cmk.utils.livestatus_helpers.expressions import And, QueryExpression
from cmk.utils.livestatus_helpers.queries import Query
from cmk.utils.livestatus_helpers.tables import Hosts, Services

from cmk.gui import http, sites
from cmk.gui.http import Response
from cmk.gui.livestatus_utils.commands.acknowledgments import (
    acknowledge_host_problem,
    acknowledge_hostgroup_problem,
    acknowledge_service_problem,
    acknowledge_servicegroup_problem,
    remove_acknowledgement,
)
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.acknowledgement.request_schemas import (
    AcknowledgeHostRelatedProblem,
    AcknowledgeServiceRelatedProblem,
    RemoveProblemAcknowledgement,
)
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.utils import permission_verification as permissions

from cmk import fields

SERVICE_DESCRIPTION = {
    "service_description": fields.String(
        description="The service name.",
        example="Memory",
    )
}

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("action.acknowledge"),
        permissions.Undocumented(
            permissions.AnyPerm(
                [
                    permissions.Perm("general.see_all"),
                    permissions.OkayToIgnorePerm("bi.see_all"),
                    permissions.OkayToIgnorePerm("mkeventd.seeall"),
                    permissions.Perm("wato.see_all_folders"),
                ]
            )
        ),
    ]
)


@Endpoint(
    constructors.collection_href("acknowledge", "host"),
    "cmk/create",
    method="post",
    tag_group="Monitoring",
    skip_locking=True,
    additional_status_codes=[422],
    status_descriptions={
        422: "The query yielded no result.",
    },
    request_schema=AcknowledgeHostRelatedProblem,
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
    update_config_generation=False,
)
def set_acknowledgement_on_hosts(params: Mapping[str, Any]) -> Response:
    """Set acknowledgement on related hosts"""
    body = params["body"]
    live = sites.live()

    sticky = body["sticky"]
    notify = body["notify"]
    persistent = body["persistent"]
    comment = body["comment"]
    expire_on = body.get("expire_on")

    acknowledge_type = body["acknowledge_type"]

    if acknowledge_type == "host":
        name = body["host_name"]
        host_state = Query([Hosts.state], Hosts.name == name).value(live)
        if not host_state:
            raise ProblemException(
                status=422,
                title=f"Host {name!r} has no problem.",
                detail="You can't acknowledge a problem that doesn't exist.",
            )
        acknowledge_host_problem(
            live,
            name,
            sticky=sticky,
            notify=notify,
            persistent=persistent,
            user=user.ident,
            comment=comment,
            expire_on=expire_on,
        )
    elif acknowledge_type == "hostgroup":
        host_group = body["hostgroup_name"]
        try:
            acknowledge_hostgroup_problem(
                live,
                host_group,
                sticky=sticky,
                notify=notify,
                persistent=persistent,
                user=user.ident,
                comment=comment,
                expire_on=expire_on,
            )
        except ValueError:
            raise ProblemException(
                400,
                title="Host group could not be found.",
                detail=f"Unknown host group: {host_group}",
            )
    elif acknowledge_type == "host_by_query":
        query = body["query"]
        hosts = Query([Hosts.name], query).fetchall(live)
        if not hosts:
            raise ProblemException(
                status=422,
                title="No hosts found",
                detail="The provided query returned no monitored hosts",
            )
        for host in hosts:
            acknowledge_host_problem(
                live,
                host.name,
                sticky=sticky,
                notify=notify,
                persistent=persistent,
                user=user.ident,
                comment=comment,
                expire_on=expire_on,
            )
    else:
        raise ProblemException(
            status=400,
            title="Unhandled acknowledge-type.",
            detail=f"The acknowledge-type {acknowledge_type!r} is not supported.",
        )

    return http.Response(status=204)


@Endpoint(
    constructors.collection_href("acknowledge", "service"),
    "cmk/create_service",
    method="post",
    tag_group="Monitoring",
    skip_locking=True,
    additional_status_codes=[422],
    status_descriptions={
        422: "Service was not in a problem state.",
    },
    request_schema=AcknowledgeServiceRelatedProblem,
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
    update_config_generation=False,
)
def set_acknowledgement_on_services(params: Mapping[str, Any]) -> Response:
    """Set acknowledgement on related services"""
    body = params["body"]
    live = sites.live()

    sticky = body["sticky"]
    notify = body["notify"]
    persistent = body["persistent"]
    comment = body["comment"]
    expire_on = body.get("expire_on")
    acknowledge_type = body["acknowledge_type"]

    if acknowledge_type == "service":
        description: str = unquote(body["service_description"])
        host_name: str = body["host_name"]
        service = Query(
            [Services.host_name, Services.description, Services.state],
            And(Services.host_name == host_name, Services.description == description),
        ).first(live)
        if not service:
            raise ProblemException(
                status=400,
                title="Service not found",
                detail=f"Service {description!r}@{host_name!r} could not be found.",
            )
        if not service.state:
            raise ProblemException(
                status=422,
                title="This service has no problem",
                detail=f"Service {description!r}@{host_name!r} has no problem.",
            )
        acknowledge_service_problem(
            live,
            service.host_name,
            service.description,
            sticky=sticky,
            notify=notify,
            persistent=persistent,
            user=user.ident,
            comment=comment,
            expire_on=expire_on,
        )
    elif acknowledge_type == "servicegroup":
        service_group = body["servicegroup_name"]
        try:
            acknowledge_servicegroup_problem(
                live,
                service_group,
                sticky=sticky,
                notify=notify,
                persistent=persistent,
                user=user.ident,
                comment=comment,
                expire_on=expire_on,
            )
        except ValueError:
            raise ProblemException(
                status=400,
                title="Service group could not be found.",
                detail=f"Unknown service group: {service_group}",
            )
    elif acknowledge_type == "service_by_query":
        services = Query(
            [Services.host_name, Services.description, Services.state],
            body["query"],
        ).fetchall(live)
        if not services:
            raise ProblemException(
                status=422,
                title="No services with problems found.",
                detail="All queried services are OK.",
            )

        # We need to check for this permission, even if we don't have a single service
        user.need_permission("action.acknowledge")
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
                user=user.ident,
                comment=comment,
                expire_on=expire_on,
            )
    else:
        raise ProblemException(
            status=400,
            title="Unhandled acknowledge-type.",
            detail=f"The acknowledge-type {acknowledge_type!r} is not supported.",
        )

    return http.Response(status=204)


def _delete_host_acknowledgements_with_query(
    query: QueryExpression,
) -> None:
    live = sites.live()
    results = Query([Hosts.name], query).fetchall(live, include_site_ids=True)
    for entry in results:
        remove_acknowledgement(
            live,
            site_id=entry["site"],
            host_name=entry[Hosts.name.name],
        )


def _delete_service_acknowledgements_with_query(
    query: QueryExpression,
) -> None:
    live = sites.live()
    results = Query([Services.host_name, Services.description], query).fetchall(
        live, include_site_ids=True
    )
    for entry in results:
        remove_acknowledgement(
            live,
            site_id=entry["site"],
            host_name=entry[Services.host_name.name],
            service_description=entry[Services.description.name],
        )


@Endpoint(
    constructors.domain_type_action_href("acknowledge", "delete"),
    ".../delete",
    method="post",
    tag_group="Monitoring",
    skip_locking=True,
    request_schema=RemoveProblemAcknowledgement,
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
    update_config_generation=False,
)
def delete_acknowledgement(params: Mapping[str, Any]) -> Response:
    """Remove acknowledgement on host or service problems."""
    user.need_permission("action.acknowledge")
    body = params["body"]
    acknowledge_type = body["acknowledge_type"]

    if acknowledge_type == "host":
        _delete_host_acknowledgements_with_query(
            And(Hosts.acknowledged > 0, Hosts.name == body["host_name"])
        )

    elif acknowledge_type == "hostgroup":
        _delete_host_acknowledgements_with_query(
            # equals() means contains, contains() means regex match :)
            And(Hosts.acknowledged > 0, Hosts.groups.equals(body["hostgroup_name"]))
        )

    elif acknowledge_type == "host_by_query":
        _delete_host_acknowledgements_with_query(body["query"])

    elif acknowledge_type == "service":
        _delete_service_acknowledgements_with_query(
            And(
                Services.acknowledged > 0,
                Services.host_name == body["host_name"],
                Services.description == body["service_description"],
            )
        )

    elif acknowledge_type == "servicegroup":
        _delete_service_acknowledgements_with_query(
            # equals() means contains, contains() means regex match :)
            And(Services.acknowledged > 0, Services.groups.equals(body["servicegroup_name"]))
        )

    elif acknowledge_type == "service_by_query":
        _delete_service_acknowledgements_with_query(body["query"])

    else:
        raise ProblemException(
            status=400,
            title="Unhandled acknowledge-type.",
            detail=f"The acknowledge-type {acknowledge_type!r} is not supported.",
        )

    return http.Response(status=204)


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(set_acknowledgement_on_hosts, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(set_acknowledgement_on_services, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete_acknowledgement, ignore_duplicates=ignore_duplicates)
