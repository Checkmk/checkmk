#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Annotated, Literal

from livestatus import OnlySites

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.mkeventd._openapi.commands import (
    filter_historical_events_table,
    HistoricalPhaseType,
    ServiceStateType,
)
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import DomainObjectCollectionModel
from cmk.gui.openapi.framework.model.common_fields import query_expression_validator
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.livestatus_client.expressions import QueryExpression
from cmk.livestatus_client.tables.eventconsolehistory import Eventconsolehistory

from .endpoint_family import HISTORICAL_EVENTS_FAMILY
from .models.response_models import HistoricalEventModel
from .permissions import PERMISSIONS

type _EventconsolehistoryQuery = Annotated[
    QueryExpression, query_expression_validator(Eventconsolehistory)
]


@api_model
class HistoricalEventsCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["historical_event"] = api_field(
        description="The domain type of the objects in the collection",
        example="historical_event",
    )
    value: list[HistoricalEventModel] = api_field(
        description="A list of historical event objects.",
        example=[
            {
                "id": "42",
                "event_id": 42,
                "history": [
                    {
                        "action": "NEW",
                        "phase": "open",
                        "state": "ok",
                        "count": 1,
                        "last": "2017-11-09T17:32:28Z",
                        "text": "Sample message text",
                        "application": "app_1",
                    }
                ],
                "links": {"self": {"href": "/mkeventd/historical_events/42"}},
            }
        ],
    )


def list_historical_events_unstable(
    api_context: ApiContext,
    site_id: Annotated[
        SiteId | ApiOmitted,
        QueryParam(
            description="The ID of the site the historical event belongs to.",
            example="prod",
        ),
    ] = ApiOmitted(),
    event_ids: Annotated[
        list[int] | ApiOmitted,
        QueryParam(
            description="A list of IDs of the historical events.",
            example=[42],
            is_list=True,
        ),
    ] = ApiOmitted(),
    host: Annotated[
        str | ApiOmitted,
        QueryParam(
            description="The host name of the historical event.",
            example="host1",
        ),
    ] = ApiOmitted(),
    application: Annotated[
        str | ApiOmitted,
        QueryParam(
            description="The application name of the historical event.",
            example="app1",
        ),
    ] = ApiOmitted(),
    state: Annotated[
        ServiceStateType | ApiOmitted,
        QueryParam(
            description="The state of the historical event.",
            example="ok",
        ),
    ] = ApiOmitted(),
    phase: Annotated[
        HistoricalPhaseType | ApiOmitted,
        QueryParam(
            description="The phase of the historical event.",
            example="ack",
        ),
    ] = ApiOmitted(),
    query: Annotated[
        _EventconsolehistoryQuery | ApiOmitted,
        QueryParam(
            description=(
                "A Livestatus query expression to filter historical events. "
                "Accepts a JSON object with 'op', 'left', and 'right' for binary expressions, "
                "or 'op' and 'expr' for logical AND/OR expressions."
            ),
            example='{"op": "=", "left": "event_host", "right": "myhost"}',
        ),
    ] = ApiOmitted(),
) -> HistoricalEventsCollectionModel:
    """Show all historical events"""

    q = filter_historical_events_table(
        event_ids=event_ids if not isinstance(event_ids, ApiOmitted) else None,
        state=state if not isinstance(state, ApiOmitted) else None,
        application=application if not isinstance(application, ApiOmitted) else None,
        host=host if not isinstance(host, ApiOmitted) else None,
        phase=phase if not isinstance(phase, ApiOmitted) else None,
        query_expression=query if not isinstance(query, ApiOmitted) else None,
    )
    _site_id: OnlySites = [site_id] if not isinstance(site_id, ApiOmitted) else None

    return HistoricalEventsCollectionModel(
        id="historical_event",
        domainType="historical_event",
        value=HistoricalEventModel.historical_collection_from_internal(
            tuple(q.fetchall(sites.live(), True, _site_id))
        ),
        links=[],
        extensions={},
    )


ENDPOINT_LIST_HISTORICAL_EVENTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("historical_event"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=HISTORICAL_EVENTS_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=list_historical_events_unstable)},
)
