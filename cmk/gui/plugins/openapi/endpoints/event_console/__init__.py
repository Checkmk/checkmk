#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Event Console

With the Event Console (EC for short), Checkmk provides a fully integrated system for monitoring events
from sources including syslog, SNMP traps, Windows Event Logs, log files and own applications. Events are
not simply defined as states, but they form a category of their own and are in fact displayed as separate
information by Checkmk in the sidebar’s Overview.

The event console endpoints allow for
* Get an event console event by event id
* Get event console events with/without filters. Get all, get by query or get by filtering on specific params.
* Update & Acknowledge / Change State filtering on specific params.
* Archive events filtering on specific params.

"""
from typing import Any, Mapping

from cmk.utils.livestatus_helpers.tables.eventconsoleevents import Eventconsoleevents

from cmk.gui import fields as gui_fields
from cmk.gui import sites
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.globals import user
from cmk.gui.http import Response
from cmk.gui.livestatus_utils.commands.event_console import (
    archive_events,
    change_state,
    ECEvent,
    EventNotFoundError,
    filter_event_table,
    get_all_events,
    get_single_event_by_id,
    update_and_acknowledge,
)
from cmk.gui.plugins.openapi.endpoints.event_console.common_fields import (
    ApplicationField,
    EventIDField,
    HostNameField,
    PhaseField,
    StateField,
)
from cmk.gui.plugins.openapi.endpoints.event_console.request_schemas import (
    ChangeEventState,
    ChangeEventStateSelector,
    DeleteECEvents,
    UpdateAndAcknowledgeEvent,
    UpdateAndAcknowledgeSelector,
)
from cmk.gui.plugins.openapi.endpoints.event_console.response_schemas import (
    ECEventResponse,
    EventConsoleResponseCollection,
)
from cmk.gui.plugins.openapi.restful_objects import constructors, Endpoint, permissions
from cmk.gui.plugins.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.plugins.openapi.utils import problem, serve_json

IGNORE_PERMISSIONS = permissions.Ignore(
    permissions.AnyPerm(
        [
            permissions.Perm("mkeventd.seeall"),
            permissions.Perm("general.see_all"),
            permissions.Perm("bi.see_all"),
        ]
    )
)

UPDATE_AND_ACKNOWLEDGE_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("mkeventd.update"),
        permissions.Perm("mkeventd.update_comment"),
        permissions.Perm("mkeventd.update_contact"),
        IGNORE_PERMISSIONS,
    ]
)

CHANGE_STATE_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("mkeventd.changestate"),
        IGNORE_PERMISSIONS,
    ]
)

DEL_PERMISSION = permissions.AllPerm(
    [
        permissions.Perm("mkeventd.delete"),
        IGNORE_PERMISSIONS,
    ]
)


class FilterEventsByQuery(BaseSchema):
    query = gui_fields.query_field(
        Eventconsoleevents,
        required=False,
    )


class EventID(BaseSchema):
    event_id = EventIDField(
        required=False,
    )


class EventState(BaseSchema):
    state = StateField(
        required=False,
    )


class EventPhase(BaseSchema):
    phase = PhaseField(
        required=False,
    )


class HostName(BaseSchema):
    host = HostNameField(
        required=False,
    )


class AppName(BaseSchema):
    application = ApplicationField(
        required=False,
    )


def event_id_not_found_problem(event_id: str) -> Response:
    return problem(
        status=404,
        title="The requested event was not found",
        detail=f"Could not find event with id {event_id}.",
    )


def _serialize_event(event: ECEvent) -> DomainObject:
    returnthis = constructors.domain_object(
        domain_type="event_console",
        identifier=str(event.event_id),
        title=event.event_text,
        extensions=dict(event),
        editable=False,
        deletable=True,
    )
    return returnthis


@Endpoint(
    constructors.object_href("event_console", "{event_id}"),
    "cmk/show",
    method="get",
    tag_group="Monitoring",
    path_params=[EventID],
    response_schema=ECEventResponse,
)
def show_event(params: Mapping[str, Any]) -> Response:
    """Show an event"""
    try:
        event = get_single_event_by_id(sites.live(), int(params["event_id"]))
    except EventNotFoundError:
        return event_id_not_found_problem(params["event_id"])
    return serve_json(data=_serialize_event(event))


@Endpoint(
    constructors.collection_href("event_console"),
    ".../collection",
    method="get",
    tag_group="Monitoring",
    response_schema=EventConsoleResponseCollection,
    update_config_generation=False,
    query_params=[FilterEventsByQuery, HostName, AppName, EventState, EventPhase],
)
def show_events(params: Mapping[str, Any]) -> Response:
    """Show events"""
    query = filter_event_table(
        host=params.get("host"),
        state=params.get("state"),
        application=params.get("application"),
        phase=params.get("phase"),
        query=params.get("query"),
    )
    return serve_json(
        constructors.collection_object(
            domain_type="event_console",
            value=[_serialize_event(ev) for _, ev in get_all_events(sites.live(), query).items()],
        )
    )


@Endpoint(
    constructors.object_action_href("event_console", "{event_id}", "update_and_acknowledge"),
    "cmk/update_and_acknowledge",
    method="post",
    tag_group="Monitoring",
    path_params=[EventID],
    request_schema=UpdateAndAcknowledgeEvent,
    output_empty=True,
    permissions_required=UPDATE_AND_ACKNOWLEDGE_PERMISSIONS,
)
def update_and_acknowledge_event(params: Mapping[str, Any]) -> Response:
    """Update and acknowledge an event"""
    user.need_permission("mkeventd.update")
    user.need_permission("mkeventd.update_comment")
    user.need_permission("mkeventd.update_contact")
    body = params["body"]
    query = filter_event_table(event_id=params["event_id"])
    results = update_and_acknowledge(
        sites.live(),
        body.get("change_comment", ""),
        body.get("change_contact", ""),
        query,
    )

    if not results:
        return event_id_not_found_problem(params["event_id"])
    return Response(status=204)


@Endpoint(
    constructors.object_action_href("event_console", "{event_id}", "change_state"),
    "cmk/change_state",
    method="post",
    tag_group="Monitoring",
    path_params=[EventID],
    request_schema=ChangeEventState,
    output_empty=True,
    permissions_required=CHANGE_STATE_PERMISSIONS,
)
def change_event_state(params: Mapping[str, Any]) -> Response:
    """Change event state"""
    user.need_permission("mkeventd.changestate")
    query = filter_event_table(event_id=params["event_id"])
    results = change_state(sites.live(), params["body"]["new_state"], query)
    if not results:
        return event_id_not_found_problem(params["event_id"])
    return Response(status=204)


@Endpoint(
    constructors.domain_type_action_href("event_console", "update_and_acknowledge"),
    ".../collection_update_and_acknowledge",
    method="post",
    tag_group="Monitoring",
    request_schema=UpdateAndAcknowledgeSelector,
    output_empty=True,
    update_config_generation=False,
    permissions_required=UPDATE_AND_ACKNOWLEDGE_PERMISSIONS,
)
def update_and_acknowledge_multiple_events(params: Mapping[str, Any]) -> Response:
    """Update and acknowledge events"""
    user.need_permission("mkeventd.update")
    user.need_permission("mkeventd.update_comment")
    user.need_permission("mkeventd.update_contact")
    body = params["body"]
    if body["filter_type"] == "params":
        filters = body["filters"]
        update_query = filter_event_table(
            host=filters.get("host"),
            state=filters.get("state"),
            application=filters.get("application"),
            phase="open",
        )
    if body["filter_type"] == "query":
        update_query = filter_event_table(
            query=body.get("query"),
            phase="open",
        )

    update_and_acknowledge(
        sites.live(),
        body.get("change_comment", ""),
        body.get("change_contact", ""),
        update_query,
    )
    return Response(status=204)


@Endpoint(
    constructors.domain_type_action_href("event_console", "change_state"),
    ".../collection_change_state",
    method="post",
    tag_group="Monitoring",
    request_schema=ChangeEventStateSelector,
    output_empty=True,
    update_config_generation=False,
    permissions_required=CHANGE_STATE_PERMISSIONS,
)
def change_multiple_event_states(params: Mapping[str, Any]) -> Response:
    """Change multiple event states"""
    user.need_permission("mkeventd.changestate")
    body = params["body"]
    if body["filter_type"] == "params":
        filters = body["filters"]
        change_state_query = filter_event_table(
            host=filters.get("host"),
            state=filters.get("state"),
            application=filters.get("application"),
            phase=filters.get("phase"),
        )
    if body["filter_type"] == "query":
        change_state_query = filter_event_table(query=body.get("query"))

    change_state(sites.live(), body["new_state"], change_state_query)
    return Response(status=204)


@Endpoint(
    constructors.domain_type_action_href("event_console", "delete"),
    ".../delete",
    method="post",
    tag_group="Monitoring",
    request_schema=DeleteECEvents,
    output_empty=True,
    permissions_required=DEL_PERMISSION,
)
def archive_events_with_filter(params: Mapping[str, Any]) -> Response:
    """Archive events"""
    user.need_permission("mkeventd.delete")
    body = params["body"]
    if body["filter_type"] == "params":
        filters = body["filters"]
        del_query = filter_event_table(
            host=filters.get("host"),
            state=filters.get("state"),
            application=filters.get("application"),
            phase=filters.get("phase"),
            query=filters.get("query"),
        )
    if body["filter_type"] == "by_id":
        del_query = filter_event_table(event_id=body["event_id"])

    if body["filter_type"] == "query":
        del_query = filter_event_table(query=body["query"])

    archive_events(sites.live(), del_query)
    return Response(status=204)
