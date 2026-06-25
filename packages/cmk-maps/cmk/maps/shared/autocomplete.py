#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared GUI↔daemon object-autocomplete query builder for Checkmk Maps.

The editor's object picker (host / service / host- and service-group name
autocomplete) runs the same server-side LQL query on both sides: filter by the
typed substring with a case-insensitive regex (``~~``) and hard-cap with
``Limit`` so a multi-million-object site filters + bounds at the source instead
of streaming every name into the editor. The daemon (``cmk.maps.backend``) and
the GUI (``cmk.maps.gui``) can't import each other (module-layer boundary), so
the query construction lives here in ``cmk.maps.shared`` — the same seam as
``cmk.maps.shared.states``.

The row execution and extraction stay on each side (sync vs async, and each
side's typed row helpers). Two knobs are injected rather than hard-coded so
this stays a pure ``cmk.maps.shared`` helper with no livestatus-layer dependency and
each side keeps its own values:

* ``escape`` — the LQL value escaper. Both sides pass ``lqencode``; it is a
  parameter only to keep ``cmk.maps.shared`` free of a livestatus import.
* ``limit`` — the GUI caps its picker list tighter than the daemon's API
  default, so the cap is per-caller.
"""

import re
from collections.abc import Callable, Iterable


def object_autocomplete_query(
    obj_type: str,
    *,
    escape: Callable[[str], str],
    limit: int,
    host: str | None = None,
    search: str | None = None,
) -> str | None:
    """Build the LQL autocomplete query for ``obj_type`` (None for unknown types).

    Every type selects the one name column the picker binds an object to, so
    both sides read row ``0`` and nothing else. For services that is the bare
    description, which is what a map object stores in ``service_description``.
    Descriptions repeat across hosts, so an unscoped service search returns the
    same name once per host — callers drop the repeats (see ``unique_names``).
    """
    q = (search or "").strip()

    def name_filter(column: str) -> str:
        # ``~~`` is a case-insensitive *regex* match — regex-escape the typed
        # substring or a literal ``(``/``[``/``+`` makes Livestatus reject the
        # whole query.
        return f"Filter: {column} ~~ {escape(re.escape(q))}\n" if q else ""

    if obj_type == "host":
        return f"GET hosts\nColumns: name\n{name_filter('name')}Limit: {limit}\n"
    if obj_type == "service":
        # Scope to one host — fetching every service times out at scale.
        host_filter = f"Filter: host_name = {escape(host)}\n" if host else ""
        return (
            f"GET services\nColumns: description\n"
            f"{host_filter}{name_filter('description')}Limit: {limit}\n"
        )
    if obj_type == "hostgroup":
        return f"GET hostgroups\nColumns: name\n{name_filter('name')}Limit: {limit}\n"
    if obj_type == "servicegroup":
        return f"GET servicegroups\nColumns: name\n{name_filter('name')}Limit: {limit}\n"
    return None


def unique_names(names: Iterable[str]) -> list[str]:
    """The names in the order the query returned them, each only once.

    A service search that is not scoped to one host reads the same description
    from every host running it; the picker offers a name, so the repeats carry
    nothing it could act on.
    """
    return list(dict.fromkeys(names))
