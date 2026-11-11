#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Protocol

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.query_filters import lq_logic
from cmk.gui.type_defs import ColumnName
from cmk.gui.visuals.filter.drilldowns import RowValues


class LinkedService(Protocol):
    """A service whose contextual links read its row."""

    @property
    def site_id(self) -> SiteId: ...

    @property
    def host_name(self) -> HostName: ...

    @property
    def service_description(self) -> str: ...


def link_host_rows(
    services: Sequence[LinkedService], columns: Sequence[ColumnName]
) -> Mapping[tuple[SiteId, HostName], RowValues]:
    """The hosts of the services with the columns the custom links' filters read; none without
    such filters, as the services name their hosts already."""
    query_columns = ["host_name", *(column for column in columns if column != "host_name")]
    if query_columns == ["host_name"] or not services:
        return {}
    query = f"GET hosts\nColumns: {' '.join(query_columns)}\n" + lq_logic(
        "Filter: host_name =", sorted({service.host_name for service in services}), "Or"
    )
    return {
        (SiteId(str(row["site"])), HostName(str(row["host_name"]))): row
        for row in _rows(services, query, query_columns)
    }


def link_service_rows(
    services: Sequence[LinkedService], columns: Sequence[ColumnName]
) -> Mapping[tuple[SiteId, HostName, str], RowValues]:
    """The services with the columns the links' filters read, host ones included."""
    if not services:
        return {}
    key_columns = ["host_name", "service_description"]
    query_columns = [*key_columns, *(column for column in columns if column not in key_columns)]
    # Hosts and services filter apart, so more pairs than listed may come back.
    query = (
        f"GET services\nColumns: {' '.join(query_columns)}\n"
        + lq_logic("Filter: host_name =", sorted({s.host_name for s in services}), "Or")
        + lq_logic(
            "Filter: service_description =",
            sorted({s.service_description for s in services}),
            "Or",
        )
    )
    return {
        (
            SiteId(str(row["site"])),
            HostName(str(row["host_name"])),
            str(row["service_description"]),
        ): row
        for row in _rows(services, query, query_columns)
    }


def _rows(
    services: Sequence[LinkedService], query: str, columns: Sequence[ColumnName]
) -> list[RowValues]:
    with (
        sites.only_sites(sorted({service.site_id for service in services})),
        sites.prepend_site(),
    ):
        return [dict(zip(["site", *columns], values)) for values in sites.live().query(query)]
