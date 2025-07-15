#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
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

For a detailed list of columns, please take a look at the [downtimes table](#section/Table-definitions/Downtimes-Table) definition.

### Relations

Downtime object can have the following relations:

 * `self` - The downtime itself.
 * `urn:com.checkmk:rels/host_config` - The host the downtime applies to.
 * `urn:org.restfulobjects/delete` - The endpoint to delete downtimes.

"""

import datetime as dt
import json
from collections.abc import Callable, Iterable, Mapping
from typing import Any, Literal

from cmk.ccc.site import SiteId

from cmk.utils.livestatus_helpers.expressions import And, Or, QueryExpression
from cmk.utils.livestatus_helpers.queries import detailed_connection, Query, ResultRow
from cmk.utils.livestatus_helpers.tables import Hosts
from cmk.utils.livestatus_helpers.tables.downtimes import Downtimes

from cmk.gui import fields as gui_fields
from cmk.gui import sites
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.http import Response
from cmk.gui.livestatus_utils.commands import downtimes as downtime_commands
from cmk.gui.livestatus_utils.commands.downtimes import QueryException
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.downtime.request_schemas import (
    CreateHostRelatedDowntime,
    CreateServiceRelatedDowntime,
    DeleteDowntime,
    DOWNTIME_ID,
    ModifyDowntime,
)
from cmk.gui.openapi.endpoints.downtime.response_schemas import DowntimeCollection, DowntimeObject
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import CollectionObject, DomainObject
from cmk.gui.openapi.spec.utils import LIVESTATUS_GENERIC_EXPLANATION
from cmk.gui.openapi.utils import problem, serve_json
from cmk.gui.utils import permission_verification as permissions

from cmk import fields

DowntimeType = Literal[
    "host", "service", "hostgroup", "servicegroup", "host_by_query", "service_by_query"
]

FindByType = Literal["query", "by_id", "params", "hostgroup", "servicegroup"]

SERVICE_DESCRIPTION_SHOW = {
    "service_description": fields.String(
        description="The service name. No exception is raised when the specified service "
        "description does not exist. This parameter can be combined with the host_name parameter "
        "to only filter for service downtimes of on a specific host. Cannot be used "
        "together with the query parameter.",
        example="Memory",
        required=False,
    )
}

HOST_NAME_SHOW = {
    "host_name": gui_fields.HostField(
        description="The host name. No exception is raised when the specified host name does not "
        "exist. Using this parameter only will filter for host downtimes only. Cannot "
        "be used together with the query parameter.",
        should_exist=None,  # we do not care
        example="example.com",
        required=False,
    )
}

DOWNTIME_TYPE = {
    "downtime_type": fields.String(
        description="The type of the downtime to be listed. Only filters the result when using "
        "the host_name or service_description parameter.",
        enum=["host", "service", "both"],
        example="host",
        load_default="both",
        required=False,
    )
}

PERMISSIONS = permissions.Undocumented(
    permissions.AnyPerm(
        [
            permissions.Perm("general.see_all"),
            permissions.OkayToIgnorePerm("bi.see_all"),
            permissions.OkayToIgnorePerm("mkeventd.seeall"),
            permissions.Perm("wato.see_all_folders"),
        ]
    )
)


RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("action.downtimes"),
        PERMISSIONS,
    ]
)


class DowntimeParameter(BaseSchema):
    query = gui_fields.query_field(
        Downtimes,
        required=False,
        example=json.dumps(
            {
                "op": "and",
                "expr": [
                    {"op": "=", "left": "host_name", "right": "example.com"},
                    {"op": "=", "left": "type", "right": "0"},
                ],
            }
        ),
    )


@Endpoint(
    constructors.collection_href("downtime", "host"),
    "cmk/create_host",
    method="post",
    tag_group="Monitoring",
    skip_locking=True,
    request_schema=CreateHostRelatedDowntime,
    additional_status_codes=[422],
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
    update_config_generation=False,
    status_descriptions={
        204: "Create host related downtimes commands have been sent to Livestatus. "
        + LIVESTATUS_GENERIC_EXPLANATION
    },
)
def create_host_related_downtime(params: Mapping[str, Any]) -> Response:
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


def _with_defaulted_timezone(
    date: dt.datetime,
    _get_local_timezone: Callable[[], dt.tzinfo | None] = lambda: dt.datetime.now(dt.UTC)
    .astimezone()
    .tzinfo,
) -> dt.datetime:
    """Default a datetime to the local timezone.

    Params:
        date: a datetime that might not have a timezone

    Returns: The input datetime if it had a timezone set or
             the input datetime with the local timezone if no timezone was set.
    """
    if date.tzinfo is None:
        date = date.replace(tzinfo=_get_local_timezone())
    return date


@Endpoint(
    constructors.collection_href("downtime", "service"),
    "cmk/create_service",
    method="post",
    tag_group="Monitoring",
    skip_locking=True,
    request_schema=CreateServiceRelatedDowntime,
    additional_status_codes=[422],
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
    update_config_generation=False,
    status_descriptions={
        204: "Create service related downtimes commands have been sent to Livestatus. "
        + LIVESTATUS_GENERIC_EXPLANATION
    },
)
def create_service_related_downtime(params: Mapping[str, Any]) -> Response:
    """Create a service related scheduled downtime"""
    body = params["body"]
    live = sites.live()

    downtime_type: DowntimeType = body["downtime_type"]

    if downtime_type == "service":
        host_name = body["host_name"]
        with detailed_connection(live) as conn:
            try:
                site_id = Query(
                    columns=[Hosts.name], filter_expr=Hosts.name.op("=", host_name)
                ).value(conn)
            except ValueError:
                # Request user can't see the host (but may still be able to access the service)
                site_id = None
        start_time = _with_defaulted_timezone(body["start_time"])
        end_time = _with_defaulted_timezone(body["end_time"])
        downtime_commands.schedule_service_downtime(
            live,
            site_id,
            host_name=body["host_name"],
            service_description=body["service_descriptions"],
            start_time=start_time,
            end_time=end_time,
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
        DOWNTIME_TYPE,
        {
            "site_id": gui_fields.SiteField(
                description="An existing site id",
                example="heute",
                presence="should_exist",
            )
        },
    ],
    response_schema=DowntimeCollection,
    permissions_required=PERMISSIONS,
)
def show_downtimes(param: Mapping[str, Any]) -> Response:
    """Show all scheduled downtimes"""
    return _show_downtimes(param)


def _show_downtimes(param: Mapping[str, Any]) -> Response:
    """
    Examples:

        >>> import json
        >>> from cmk.gui.livestatus_utils.testing import simple_expect
        >>> from cmk.gui.openapi.restful_objects.params import marshmallow_to_openapi
        >>> from cmk.gui.fields.utils import tree_to_expr
        >>> with simple_expect() as live:
        ...    _ = live.expect_query("GET downtimes\\nColumns: host_name type\\nFilter: host_name = example.com\\nFilter: type = 0\\nAnd: 2")
        ...    q = Query([Downtimes.host_name, Downtimes.type])
        ...    q = q.filter(tree_to_expr(json.loads(marshmallow_to_openapi([DowntimeParameter], "query")[0]['example']), "downtimes"))
        ...    list(q.iterate(live))
        []

    """

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
    host_name = param.get("host_name")
    service_description = param.get("service_description")

    if (downtime_type := param["downtime_type"]) != "both":
        q = q.filter(Downtimes.is_service.equals(1 if downtime_type == "service" else 0))

    if query_expr is not None:
        q = q.filter(query_expr)

    if host_name is not None:
        q = q.filter(Downtimes.host_name.op("=", host_name))

    if service_description is not None:
        q = q.filter(Downtimes.service_description.contains(service_description))

    _site_id: SiteId | None = param.get("site_id")
    return serve_json(
        _serialize_downtimes(
            q.fetchall(sites.live(), True, [_site_id] if _site_id is not None else _site_id)
        )
    )


@Endpoint(
    constructors.object_href("downtime", "{downtime_id}"),
    "cmk/show",
    method="get",
    tag_group="Monitoring",
    path_params=[{"downtime_id": DOWNTIME_ID}],
    query_params=[
        {
            "site_id": gui_fields.SiteField(
                description="An existing site id",
                example="heute",
                presence="should_exist",
                required=True,
            )
        }
    ],
    response_schema=DowntimeObject,
    permissions_required=PERMISSIONS,
)
def show_downtime(params: Mapping[str, Any]) -> Response:
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
        downtime = q.fetchone(live, True, SiteId(params["site_id"]))
    except ValueError:
        return problem(
            status=404,
            title="The requested downtime was not found",
            detail=f"The downtime id {downtime_id} did not match any downtime",
        )
    return serve_json(_serialize_single_downtime(downtime))


@Endpoint(
    constructors.domain_type_action_href("downtime", "delete"),
    ".../delete",
    method="post",
    tag_group="Monitoring",
    skip_locking=True,
    request_schema=DeleteDowntime,
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
    update_config_generation=False,
    status_descriptions={
        204: "Delete downtimes commands have been sent to Livestatus. "
        + LIVESTATUS_GENERIC_EXPLANATION
    },
)
def delete_downtime(params: Mapping[str, Any]) -> Response:
    """Delete a scheduled downtime"""
    body = params["body"]
    delete_type: FindByType = body["delete_type"]
    site_id: SiteId | None
    query_expr: QueryExpression

    query_expr, site_id = _generate_target_downtimes_query(delete_type, body)

    downtime_commands.delete_downtime(sites.live(), query_expr, site_id)
    return Response(status=204)


@Endpoint(
    constructors.domain_type_action_href("downtime", "modify"),
    ".../update",
    method="put",
    tag_group="Monitoring",
    skip_locking=True,
    request_schema=ModifyDowntime,
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
    update_config_generation=False,
    status_descriptions={
        204: "Update downtimes commands have been sent to Livestatus. "
        + LIVESTATUS_GENERIC_EXPLANATION
    },
)
def modify_host_downtime(params: Mapping[str, Any]) -> Response:
    """Modify a scheduled downtime"""
    body = params["body"]
    update_type: FindByType = body["modify_type"]
    site_id: SiteId | None
    query_expr: QueryExpression

    query_expr, site_id = _generate_target_downtimes_query(update_type, body)

    end_time = body.get("end_time")
    comment = body.get("comment")

    if end_time is None and comment is None:
        return problem(
            status=400,
            title="No modification specified",
            detail="You must especify at least one field to modify",
        )

    end_time_value = None if end_time is None else end_time.get("value")

    downtime_commands.modify_downtimes(
        sites.live(),
        query_expr,
        site_id,
        user_id=user.ident,
        end_time=end_time_value,
        comment=comment,
    )

    return Response(status=204)


def _generate_target_downtimes_query(
    find_type: FindByType, body: Mapping[str, Any]
) -> tuple[QueryExpression, SiteId | None]:
    site_id: SiteId | None = None

    if find_type == "query":
        query_expr = body["query"]

    elif find_type == "by_id":
        query_expr = Downtimes.id == body["downtime_id"]
        site_id = SiteId(body["site_id"])
    elif find_type == "hostgroup":
        query_expr = Downtimes.host_groups.contains(body["hostgroup_name"])
    elif find_type == "servicegroup":
        query_expr = Downtimes.service_groups.contains(body["servicegroup_name"])
    else:
        hostname = body["host_name"]
        if "service_descriptions" not in body:
            query_expr = And(Downtimes.host_name.op("=", hostname), Downtimes.is_service.op("=", 0))
        else:
            query_expr = And(
                Downtimes.host_name.op("=", hostname),
                Or(
                    *[
                        Downtimes.service_description == svc_desc
                        for svc_desc in body["service_descriptions"]
                    ]
                ),
            )
    return query_expr, site_id


def _serialize_downtimes(downtimes: Iterable[ResultRow]) -> CollectionObject:
    return constructors.collection_object(
        "downtime",
        value=[_serialize_single_downtime(downtime) for downtime in downtimes],
    )


def _serialize_single_downtime(downtime: ResultRow) -> DomainObject:
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


def _downtime_properties(info: ResultRow) -> dict[str, Any]:
    downtime = {
        "site_id": info["site"],
        "host_name": info["host_name"],
        "author": info["author"],
        "is_service": bool(info["is_service"]),
        "start_time": info["start_time"],
        "end_time": info["end_time"],
        "recurring": bool(info["recurring"]),
        "comment": info["comment"],
    }

    if info["is_service"]:
        downtime["service_description"] = info["service_description"]

    return downtime


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(create_host_related_downtime, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(create_service_related_downtime, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_downtimes, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_downtime, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete_downtime, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(modify_host_downtime, ignore_duplicates=ignore_duplicates)
