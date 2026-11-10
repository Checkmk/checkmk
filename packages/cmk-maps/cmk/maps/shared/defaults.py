#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Factory defaults shared between the Maps daemon and the GUI configuration."""

from typing import Literal, TypedDict

# Seconds. Cold-start Livestatus calls on busy sites can take longer than 10 s.
DEFAULT_CONNECTION_TIMEOUT = 30


class LivestatusOptions(TypedDict):
    """The Livestatus arm of the connection form's ``type`` cascade."""

    target: tuple[Literal["local"], None]
    timeout: int
    metric_history: tuple[Literal["livestatus"], None]


class ConnectionEntry(TypedDict):
    """One ``maps_connections`` entry in the nested FormSpec shape WATO stores.

    The daemon flattens this back into a ``ConnectionConfig``
    (``cmk.maps.backend.services.connection_forms``).
    """

    id: str
    label: str
    type: tuple[Literal["livestatus"], LivestatusOptions]


def default_connections(site: str) -> list[ConnectionEntry]:
    """The connections of a site that has none configured: one to its own Livestatus.

    The GUI shows them as the factory setting and never writes them to the file
    the daemon reads, so the daemon takes them from here too.
    """
    return [
        {
            "id": f"cmk_{site}",
            "label": f"Checkmk {site}",
            "type": (
                "livestatus",
                {
                    "target": ("local", None),
                    "timeout": DEFAULT_CONNECTION_TIMEOUT,
                    "metric_history": ("livestatus", None),
                },
            ),
        }
    ]
