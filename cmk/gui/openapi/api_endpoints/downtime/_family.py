#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

DOWNTIME_FAMILY = EndpointFamily(
    name="Downtimes",
    description="""\
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
""",
    doc_group="Monitoring",
)
