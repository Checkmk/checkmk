#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.livestatus_client._connection import RRDResponse, SingleSiteConnection
from cmk.livestatus_client.expressions import And
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables.hosts import Hosts
from cmk.livestatus_client.tables.services import Services


def get_rrd_data(
    connection: SingleSiteConnection,
    host_name: str,
    service_description: str,
    rpn: str,
    fromtime: int,
    untiltime: int,
    max_entries: int = 400,
) -> RRDResponse | None:
    """Fetch RRD historic metrics data of a specific service, within the specified time range

    returns a TimeSeries object holding interval and data information

    Query to livestatus always returns if database is found, thus:
    - Values can be None when there is no data for a given timestamp
    - Reply from livestatus/rrdtool is always enough to describe the
      queried interval. That means, the returned bounds are always outside
      the queried interval.

    LEGEND
    O timestamps of measurements
    | query values, fromtime and untiltime
    x returned start, no data contained
    v returned data rows, includes end y

    --O---O---O---O---O---O---O---O
            |---------------|
          x---v---v---v---v---y

    """

    step = 1
    # Host metrics are stored under the `_HOST_` sentinel and live on the hosts table.
    # `dynamic` validates all parts of the column.
    query: Query
    if service_description == "_HOST_":
        query = Query(
            [Hosts.rrddata.dynamic("m1", rpn, fromtime, untiltime, step, max_entries)],
            Hosts.name == host_name,
        )
    else:
        query = Query(
            [Services.rrddata.dynamic("m1", rpn, fromtime, untiltime, step, max_entries)],
            And(
                Services.host_name == host_name,
                Services.description == service_description,
            ),
        )

    # This can raise, but let the caller deal with it.
    response = connection.query_value(query)

    if not response:
        # Appending nonsense to the column will give you None.
        # It seems that querying in case we haven't got enough records (yet)
        # will give you an empty response as of Checkmk 2.4.
        # Not sure what that means for the comment below.
        return None

    raw_start, raw_end, raw_step, *values = response

    return (
        # According to a comment in RRDColumn.cc we should have `raw_step >= step` (which is 1)
        # However, it is zero for empty responses (non existing metrics, for instance).
        None
        if (step := int(raw_step)) == 0
        else RRDResponse(range(int(raw_start), int(raw_end), step), values)
    )
