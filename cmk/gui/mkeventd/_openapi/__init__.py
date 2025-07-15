#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Event Console

With the Event Console (EC for short), Checkmk provides a fully integrated system for monitoring events
from sources including syslog, SNMP traps, Windows Event Logs, log files and own applications. Events are
not simply defined as states, but they form a category of their own and are in fact displayed as separate
information by Checkmk in the sidebar’s Overview.

The event console endpoints allow for
* Show event console event/s.
    * Query the event console table using filters, id or live status query.
* Update & Acknowledge event/s.
    * Query the event console table using filters, id or live status query and set the phase to ack or open.
* Change State of event/s.
    * Query the event console table using filters, id or live status query and set the state for those events.
* Archive event/s.
    * Query the event console table using filters, id or live status query and archive those events.

"""

from collections.abc import Mapping
from typing import Any

from cmk.ccc.site import SiteId

from cmk.utils.livestatus_helpers.tables.eventconsoleevents import Eventconsoleevents

from cmk.gui import fields as gui_fields
from cmk.gui import sites
from cmk.gui.fields.utils import BaseSchema
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
from cmk.gui.logged_in import user
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.openapi.utils import problem, serve_json
from cmk.gui.utils import permission_verification as permissions

from .common_fields import ApplicationField, EventIDField, HostNameField, PhaseField, StateField
from .request_schemas import (
    ChangeEventState,
    ChangeEventStateSelector,
    DeleteECEvents,
    UpdateAndAcknowledeEventSiteIDRequired,
    UpdateAndAcknowledgeSelector,
)
from .response_schemas import ECEventResponse, EventConsoleResponseCollection

IGNORE_PERMISSIONS = permissions.Undocumented(
    permissions.AnyPerm(
        [
            permissions.Perm("mkeventd.seeall"),
            permissions.Perm("general.see_all"),
            permissions.OkayToIgnorePerm("bi.see_all"),
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
        example='{"op": "=", "left": "eventconsoleevents.event_host", "right": "test_host"}',
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
    return constructors.domain_object(
        domain_type="event_console",
        identifier=str(event.event_id),
        title=event.event_text,
        extensions=dict(event),
        editable=False,
        deletable=True,
    )


@Endpoint(
    constructors.object_href("event_console", "{event_id}"),
    "cmk/show",
    method="get",
    tag_group="Monitoring",
    path_params=[EventID],
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
    response_schema=ECEventResponse,
)
def show_event(params: Mapping[str, Any]) -> Response:
    """Show an event"""
    try:
        event = get_single_event_by_id(sites.live(), int(params["event_id"]), params["site_id"])
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
    query_params=[
        FilterEventsByQuery,
        HostName,
        AppName,
        EventState,
        EventPhase,
        {
            "site_id": gui_fields.SiteField(
                description="An existing site id",
                example="heute",
                presence="should_exist",
            )
        },
    ],
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
            value=[
                _serialize_event(ev)
                for _, ev in get_all_events(sites.live(), query, params.get("site_id")).items()
            ],
        )
    )


@Endpoint(
    constructors.object_action_href("event_console", "{event_id}", "update_and_acknowledge"),
    "cmk/update_and_acknowledge",
    method="post",
    tag_group="Monitoring",
    path_params=[EventID],
    request_schema=UpdateAndAcknowledeEventSiteIDRequired,
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
        body["phase"],
        body["site_id"],
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
    results = change_state(
        sites.live(), params["body"]["new_state"], query, params["body"]["site_id"]
    )
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
    # Optimization - If the user wants to acknowledge events, filter for only open events
    # if the user wants to open events, filter for only acknowledged events
    filter_phase = "ack" if body["phase"] == "open" else "open"
    match body["filter_type"]:
        case "all":
            update_query = filter_event_table(
                phase=filter_phase,
            )
        case "params":
            filters = body["filters"]
            update_query = filter_event_table(
                host=filters.get("host"),
                state=filters.get("state"),
                application=filters.get("application"),
                phase=filter_phase,
            )
        case "query":
            update_query = filter_event_table(
                query=body.get("query"),
                phase=filter_phase,
            )

    update_and_acknowledge(
        sites.live(),
        body.get("change_comment", ""),
        body.get("change_contact", ""),
        update_query,
        body["phase"],
        body.get("site_id"),
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
    match body["filter_type"]:
        case "params":
            filters = body["filters"]
            change_state_query = filter_event_table(
                host=filters.get("host"),
                state=filters.get("state"),
                application=filters.get("application"),
                phase=filters.get("phase"),
            )

        case "query":
            change_state_query = filter_event_table(
                query=body.get("query"),
            )

    change_state(sites.live(), body["new_state"], change_state_query, body.get("site_id"))
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

    site_id: SiteId | None = None
    match body["filter_type"]:
        case "params":
            filters = body["filters"]
            del_query = filter_event_table(
                host=filters.get("host"),
                state=filters.get("state"),
                application=filters.get("application"),
                phase=filters.get("phase"),
                query=filters.get("query"),
            )
        case "by_id":
            del_query = filter_event_table(event_id=body["event_id"])
            site_id = SiteId(body["site_id"])

        case "query":
            del_query = filter_event_table(query=body["query"])

    archive_events(sites.live(), del_query, site_id)
    return Response(status=204)


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(show_event, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_events, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(update_and_acknowledge_event, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(change_event_state, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(
        update_and_acknowledge_multiple_events, ignore_duplicates=ignore_duplicates
    )
    endpoint_registry.register(change_multiple_event_states, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(archive_events_with_filter, ignore_duplicates=ignore_duplicates)
