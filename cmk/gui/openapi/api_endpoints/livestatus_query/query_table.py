#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui import sites
from cmk.gui.log import logger
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.utils import permission_verification as permissions
from cmk.livestatus_client import (
    MKLivestatusException,
    MKLivestatusQueryError,
    MultiSiteConnection,
)
from cmk.livestatus_client.queries import Query, ResultRow

from ._family import LIVESTATUS_QUERY_FAMILY
from .models.request_models import LivestatusQueryBody
from .models.response_models import LivestatusQueryResponse

PERMISSIONS = permissions.Undocumented(
    permissions.AnyPerm(
        [
            permissions.Perm("general.see_all"),
            permissions.OkayToIgnorePerm("bi.see_all"),
            permissions.OkayToIgnorePerm("mkeventd.seeall"),
        ]
    )
)


def _query_rows(live: MultiSiteConnection, q: Query) -> list[ResultRow]:
    """Run the query and return its rows, containing any livestatus failure.

    Consumes the result eagerly so a livestatus error surfaces here rather than during
    serialization. Both error responses use fixed detail strings that never interpolate the
    underlying exception text, so raw socket paths, addresses, or LQL never reach the wire.
    `MKLivestatusQueryError` (a bad query) becomes a 400; any other livestatus failure (its
    superclass, e.g. a connection error, a timeout or a response parse error) becomes a 500.

    Because the wire detail is fixed, the exception itself only ever reaches the site log: both
    branches log it there, which is the sole place an operator can see what livestatus actually
    said.
    """
    try:
        return list(q.iterate(live))
    except MKLivestatusQueryError:
        logger.exception("Livestatus rejected a REST API query")
        raise ProblemException(
            status=400,
            title="Livestatus rejected the query",
            detail="The monitoring core rejected the query. Check the table, columns and filter.",
        )
    except MKLivestatusException:
        logger.exception("A REST API livestatus query failed")
        raise ProblemException(
            status=500,
            title="Livestatus error",
            detail="The query could not be completed because of a livestatus failure, "
            "e.g. a connection error or a timeout.",
        )


def query_table_v1(body: LivestatusQueryBody) -> LivestatusQueryResponse:
    """Query a Livestatus table"""
    live = sites.live()
    if body.sites:
        live.only_sites = body.sites
    live.set_limit(body.limit)
    q = body.to_query()
    return LivestatusQueryResponse.from_result(body.table, body.columns, _query_rows(live, q))


ENDPOINT_QUERY_TABLE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("livestatus_query"),
        link_relation="cmk/list",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(
        family=LIVESTATUS_QUERY_FAMILY.name,
        exclude_in_targets={"swagger-ui"},
    ),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=query_table_v1)},
)
