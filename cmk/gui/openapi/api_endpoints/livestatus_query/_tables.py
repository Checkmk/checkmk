#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The closed set of Livestatus tables this endpoint may query.

The registry enumerates its Table classes by hand (only the wire-name keys are
read off each class's ``__tablename__``); it is NOT derived at import time from
``cmk.livestatus_client.tables.__all__``, and it stays that way deliberately:

* ``__all__`` answers "what may other Python code import", while this mapping
  answers "what may any authenticated HTTP client read from the monitoring
  core". Deriving one from the other fuses the two questions, so a future export
  in the client package (say ``statehist``, added for some internal use) would
  silently widen the REST exposure surface. The explicit dict, the
  ``INTENTIONALLY_NOT_EXPOSED`` opt-out set below, and the drift-guard test
  keep every export consciously accounted for -- either REST-exposed here or
  explicitly opted out -- so a human must update one of the two when exposure
  changes.
* Wire names are looked up by exact-match dict access only. No ``getattr`` over
  a request-controlled string ever runs (the Werk #17028-class injection this
  design forecloses), and no case folding or ``.title()`` widens the match.
* CMK-36995 will attach per-table permission policy here, so an explicit dict is
  the natural seam to grow into richer per-table entries.
"""

from collections.abc import Mapping

from cmk.livestatus_client.tables import (
    Comments,
    Downtimes,
    Eventconsoleevents,
    Eventconsolehistory,
    Hostgroups,
    Hosts,
    Log,
    Servicegroups,
    Services,
    Status,
)
from cmk.livestatus_client.types import Table

LIVESTATUS_TABLES: Mapping[str, type[Table]] = {
    table.__tablename__: table
    for table in (
        Comments,
        Downtimes,
        Eventconsoleevents,
        Eventconsolehistory,
        Hostgroups,
        Hosts,
        Log,
        Servicegroups,
        Services,
        Status,
    )
}

# Class names of exported Table classes that are deliberately NOT reachable over
# REST. When a new Table is added to ``cmk.livestatus_client.tables.__all__``
# for internal use only, add its class name here: the drift-guard test then
# stays green without widening what an HTTP client may read. Empty today --
# every currently exported table IS intentionally exposed.
INTENTIONALLY_NOT_EXPOSED: frozenset[str] = frozenset()


def resolve_table(name: str) -> type[Table]:
    """Return the Table class registered under the exact wire name, else raise.

    Only the exact lowercase wire names in ``LIVESTATUS_TABLES`` resolve; every
    other string (class names, dunder attributes, unexported package modules,
    LQL-injection payloads) is rejected with a ``ValueError`` that lists the
    supported names so the resulting 400 is self-describing.
    """
    try:
        return LIVESTATUS_TABLES[name]
    except KeyError:
        supported = ", ".join(sorted(LIVESTATUS_TABLES))
        raise ValueError(f"Unknown table {name!r}. Supported tables are: {supported}") from None
