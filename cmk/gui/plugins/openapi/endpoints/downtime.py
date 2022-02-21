# , user!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Downtimes

A (scheduled) downtime is a planned maintenance period.
Hosts and services are handled differently by Checkmk during a downtime, for example,
notifications are disabled.

### Related documentation

How to use the query DSL used in the `query` parameters of these endpoints, have a look at the
[Querying Status Data](#section/Querying-Status-Data) section of this documentation.

These endpoints support all [Livestatus filter operators](https://docs.checkmk.com/latest/en/livestatus_references.html#heading_filter),
which you can look up in the Checkmk documentation.

For a detailed list of columns, please take a look at the [downtimes table](https://github.com/tribe29/checkmk/blob/master/cmk/gui/plugins/openapi/livestatus_helpers/tables/downtimes.py)
definition on GitHub.

### Relations

Downtime object can have the following relations:

 * `self` - The downtime itself.
 * `urn:com.checkmk:rels/host_config` - The host the downtime applies to.
 * `urn:org.restfulobjects/delete` - The endpoint to delete downtimes.

"""

import datetime as dt
import json
from typing import Literal

from cmk.utils.livestatus_helpers.expressions import And, Or
from cmk.utils.livestatus_helpers.queries import detailed_connection, Query
from cmk.utils.livestatus_helpers.tables import Hosts
from cmk.utils.livestatus_helpers.tables.downtimes import Downtimes

from cmk.gui import fields as gui_fields
from cmk.gui import sites
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.globals import user
from cmk.gui.http import Response
from cmk.gui.livestatus_utils.commands import downtimes as downtime_commands
from cmk.gui.livestatus_utils.commands.downtimes import QueryException
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    request_schemas,
    response_schemas,
)
from cmk.gui.plugins.openapi.utils import problem

from cmk import fields

DowntimeType = Literal[
    "host", "service", "hostgroup", "servicegroup", "host_by_query", "service_by_query"
]

SERVICE_DESCRIPTION_SHOW = {
    "service_description": fields.String(
        description="The service description. No exception is raised when the specified service "
        "description does not exist",
        example="Memory",
        required=False,
    )
}

HOST_NAME_SHOW = {
    "host_name": gui_fields.HostField(
        description="The host name. No exception is raised when the specified host name does not exist",
        should_exist=None,  # we do not care
        example="example.com",
        required=False,
    )
}


class DowntimeParameter(BaseSchema):
    query = gui_fields.query_field(Downtimes, required=False)


@Endpoint(
    constructors.collection_href("downtime", "host"),
    "cmk/create_host",
    method="post",
    tag_group="Monitoring",
    skip_locking=True,
    request_schema=request_schemas.CreateHostRelatedDowntime,
    additional_status_codes=[422],
    output_empty=True,
    update_config_generation=False,
)
def create_host_related_downtime(params):
    """Create a host related scheduled downtime"""
    body = params["body"]
    live = sites.live()

    downtime_type: DowntimeType = body["downtime_type"]

    if downtime_type == "host":
        downtime_commands.schedule_host_downtime(
            live,
            host_entry=body["host_name"],
            start_time=body["start_time"],
            end_time=body["end_time"],
            recur=body["recur"],
            duration=body["duration"],
            user_id=user.ident,
            comment=body.get("comment", f"Downtime for host {body['host_name']!r}"),
        )
    elif downtime_type == "hostgroup":
        downtime_commands.schedule_hostgroup_host_downtime(
            live,
            hostgroup_name=body["hostgroup_name"],
            start_time=body["start_time"],
            end_time=body["end_time"],
            recur=body["recur"],
            duration=body["duration"],
            user_id=user.ident,
            comment=body.get("comment", f"Downtime for hostgroup {body['hostgroup_name']!r}"),
        )

    elif downtime_type == "host_by_query":
        try:
            downtime_commands.schedule_hosts_downtimes_with_query(
                live,
                body["query"],
                start_time=body["start_time"],
                end_time=body["end_time"],
                recur=body["recur"],
                duration=body["duration"],
                user_id=user.ident,
                comment=body.get("comment", ""),
            )
        except QueryException:
            return problem(
                status=422,
                title="Query did not match any host",
                detail="The provided query returned an empty list so no downtime was set",
            )
    else:
        return problem(
            status=400,
            title="Unhandled downtime-type.",
            detail=f"The downtime-type {downtime_type!r} is not supported.",
        )

    return Response(status=204)


@Endpoint(
    constructors.collection_href("downtime", "service"),
    "cmk/create_service",
    method="post",
    tag_group="Monitoring",
    skip_locking=True,
    request_schema=request_schemas.CreateServiceRelatedDowntime,
    additional_status_codes=[422],
    output_empty=True,
    update_config_generation=False,
)
def create_service_related_downtime(params):
    """Create a service related scheduled downtime"""
    body = params["body"]
    live = sites.live()

    downtime_type: DowntimeType = body["downtime_type"]

    if downtime_type == "service":
        host_name = body["host_name"]
        with detailed_connection(live) as conn:
            site_id = Query(columns=[Hosts.name], filter_expr=Hosts.name.op("=", host_name)).value(
                conn
            )
        downtime_commands.schedule_service_downtime(
            live,
            site_id,
            host_name=body["host_name"],
            service_description=body["service_descriptions"],
            start_time=body["start_time"],
            end_time=body["end_time"],
            recur=body["recur"],
            duration=body["duration"],
            user_id=user.ident,
            comment=body.get(
                "comment",
                f"Downtime for services {', '.join(body['service_descriptions'])!r}@{body['host_name']!r}",
            ),
        )
    elif downtime_type == "servicegroup":
        downtime_commands.schedule_servicegroup_service_downtime(
            live,
            servicegroup_name=body["servicegroup_name"],
            start_time=body["start_time"],
            end_time=body["end_time"],
            recur=body["recur"],
            duration=body["duration"],
            user_id=user.ident,
            comment=body.get("comment", f"Downtime for servicegroup {body['servicegroup_name']!r}"),
        )
    elif downtime_type == "service_by_query":
        try:
            downtime_commands.schedule_services_downtimes_with_query(
                live,
                query=body["query"],
                start_time=body["start_time"],
                end_time=body["end_time"],
                recur=body["recur"],
                duration=body["duration"],
                user_id=user.ident,
                comment=body.get("comment", ""),
            )
        except QueryException:
            return problem(
                status=422,
                title="Query did not match any service",
                detail="The provided query returned an empty list so no downtime was set",
            )
    else:
        return problem(
            status=400,
            title="Unhandled downtime-type.",
            detail=f"The downtime-type {downtime_type!r} is not supported.",
        )

    return Response(status=204)


@Endpoint(
    constructors.collection_href("downtime"),
    ".../collection",
    method="get",
    tag_group="Monitoring",
    query_params=[
        HOST_NAME_SHOW,
        SERVICE_DESCRIPTION_SHOW,
        DowntimeParameter,
    ],
    response_schema=response_schemas.DomainObjectCollection,
)
def show_downtimes(param):
    """Show all scheduled downtimes"""
    live = sites.live()
    sites_to_query = param.get("sites")
    if sites_to_query:
        live.only_sites = sites_to_query

    q = Query(
        [
            Downtimes.id,
            Downtimes.host_name,
            Downtimes.service_description,
            Downtimes.is_service,
            Downtimes.author,
            Downtimes.start_time,
            Downtimes.end_time,
            Downtimes.recurring,
            Downtimes.comment,
        ]
    )

    query_expr = param.get("query")
    if query_expr is not None:
        q = q.filter(query_expr)

    host_name = param.get("host_name")
    if host_name is not None:
        q = q.filter(And(Downtimes.host_name.op("=", host_name), Downtimes.is_service.equals(0)))

    service_description = param.get("service_description")
    if service_description is not None:
        q = q.filter(Downtimes.service_description.contains(service_description))

    gen_downtimes = q.iterate(live)
    return _serve_downtimes(gen_downtimes)


@Endpoint(
    constructors.object_href("downtime", "{downtime_id}"),
    "cmk/show",
    method="get",
    path_params=[
        {
            "downtime_id": fields.Integer(
                description="The id of the downtime",
                example="1",
            )
        }
    ],
    response_schema=response_schemas.DomainObject,
)
def show_downtime(params):
    """Show downtime"""
    live = sites.live()
    downtime_id = params["downtime_id"]
    q = Query(
        columns=[
            Downtimes.id,
            Downtimes.host_name,
            Downtimes.service_description,
            Downtimes.is_service,
            Downtimes.author,
            Downtimes.start_time,
            Downtimes.end_time,
            Downtimes.recurring,
            Downtimes.comment,
        ],
        filter_expr=Downtimes.id.op("=", downtime_id),
    )

    try:
        downtime = q.fetchone(live)
    except ValueError:
        return problem(
            status=404,
            title="The requested downtime was not found",
            detail=f"The downtime id {downtime_id} did not match any downtime",
        )
    return _serve_downtime(downtime)


def _serve_downtime(downtime_details):
    response = Response()
    response.set_data(json.dumps(_serialize_single_downtime(downtime_details)))
    response.set_content_type("application/json")
    return response


@Endpoint(
    constructors.domain_type_action_href("downtime", "delete"),
    ".../delete",
    method="post",
    tag_group="Monitoring",
    skip_locking=True,
    request_schema=request_schemas.DeleteDowntime,
    output_empty=True,
    update_config_generation=False,
)
def delete_downtime(params):
    """Delete a scheduled downtime"""
    body = params["body"]
    live = sites.live()
    delete_type = body["delete_type"]
    if delete_type == "query":
        downtime_commands.delete_downtime_with_query(live, body["query"])
    elif delete_type == "by_id":
        downtime_commands.delete_downtime(live, body["downtime_id"])
    elif delete_type == "params":
        hostname = body["host_name"]
        if "service_descriptions" not in body:
            host_expr = And(Downtimes.host_name.op("=", hostname), Downtimes.is_service.op("=", 0))
            downtime_commands.delete_downtime_with_query(live, host_expr)
        else:
            services_expr = And(
                Downtimes.host_name.op("=", hostname),
                Or(
                    *[
                        Downtimes.service_description == svc_desc
                        for svc_desc in body["service_descriptions"]
                    ]
                ),
            )
            downtime_commands.delete_downtime_with_query(live, services_expr)
    else:
        return problem(
            status=400,
            title="Unhandled delete_type.",
            detail=f"The downtime-type {delete_type!r} is not supported.",
        )
    return Response(status=204)


def _serve_downtimes(downtimes):
    response = Response()
    response.set_data(json.dumps(_serialize_downtimes(downtimes)))
    response.set_content_type("application/json")
    return response


def _serialize_downtimes(downtimes):
    entries = []
    for downtime in downtimes:
        entries.append(_serialize_single_downtime(downtime))

    return constructors.collection_object(
        "downtime",
        value=entries,
    )


def _serialize_single_downtime(downtime):
    links = []
    if downtime["is_service"]:
        downtime_detail = f"service: {downtime['service_description']}"
    else:
        host_name = downtime["host_name"]
        downtime_detail = f"host: {host_name}"
        links.append(
            constructors.link_rel(
                rel="cmk/host_config",
                href=constructors.object_href("host_config", host_name),
                title="This host of this downtime.",
                method="get",
            )
        )

    downtime_id = downtime["id"]
    return constructors.domain_object(
        domain_type="downtime",
        identifier=str(downtime_id),
        title="Downtime for %s" % downtime_detail,
        extensions=_downtime_properties(downtime),
        links=[
            constructors.link_rel(
                rel=".../delete",
                href=constructors.domain_type_action_href("downtime", "delete"),
                method="post",
                title="Delete the downtime",
                body_params={"delete_type": "by_id", "downtime_id": downtime_id},
            ),
        ],
        editable=False,
        deletable=False,
    )


def _downtime_properties(info):
    return {
        "host_name": info["host_name"],
        "author": info["author"],
        "is_service": "yes" if info["is_service"] else "no",
        "start_time": _time_utc(dt.datetime.fromtimestamp(info["start_time"])),
        "end_time": _time_utc(dt.datetime.fromtimestamp(info["end_time"])),
        "recurring": "yes" if info["recurring"] else "no",
        "comment": info["comment"],
    }


def _time_utc(time_dt):
    return time_dt.strftime("%Y-%m-%dT%H:%M:%S%z")
