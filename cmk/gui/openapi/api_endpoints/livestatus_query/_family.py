#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

from ._tables import LIVESTATUS_TABLES

_KNOWN_TABLES = ", ".join(f"`{name}`" for name in sorted(LIVESTATUS_TABLES))

LIVESTATUS_QUERY_FAMILY = EndpointFamily(
    name="Livestatus query",
    description=(
        f"""A generic, machine-facing endpoint for reading monitoring data from Livestatus.

Post a body naming the `table`, the `columns` to return, an optional `query` filter expression,
an optional list of `sites`, and an optional row `limit`. The filter is a nested object, for
example:

    {{"op": "=", "left": "name", "right": "heute"}}

The following tables can be queried: {_KNOWN_TABLES}.

### Security posture (interim)

Rows are scoped to the logged-in user via the Livestatus `AuthUser` header, exactly as the
existing status endpoints are. Tables that Livestatus does not contact-scope (notably `status`)
therefore return site-global data to any authenticated user. Every query carries a row limit
(default 1000, capped at 10000), applied per site (CMK-36997). This endpoint does not yet
enforce a per-table permission allowlist (CMK-36995), which is tracked separately."""
    ),
    doc_group="Checkmk Internal",
)
