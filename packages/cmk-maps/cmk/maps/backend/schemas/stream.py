#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The messages the SSE stream pushes to a connected map.

Modelled rather than assembled as dicts at the send site so the stream travels the
same schema as the REST endpoints: the frontend's stream types are generated from
it, and a field added here cannot silently miss the client.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from cmk.maps.backend.schemas.settings import DaemonRuntime
from cmk.maps.backend.schemas.state import (
    FolderTreeDelta,
    ObjectState,
    ObjectTiming,
)
from cmk.maps.backend.schemas.topology import TopologyDelta


class StreamedMapStates(BaseModel):
    """The states of one tick as the stream carries them.

    Differs from the REST ``MapStates`` in what a tick can leave out: ``states``
    holds only the objects that changed (unless the enclosing message is ``full``),
    and a foldertree map ships a tree delta instead of the whole tree, which runs to
    tens of megabytes on a large site.
    """

    map_name: str
    states: list[ObjectState]
    generated_at: float
    connection_ok: bool = True
    dead_sites: list[str] = []
    folder_tree_delta: FolderTreeDelta | None = None
    # Same knobs the REST first paint carries, so a client that only ever sees
    # stream messages (a long-lived tab) picks up a changed cadence without
    # re-fetching.
    runtime: DaemonRuntime


class StateUpdateMessage(BaseModel):
    type: Literal["state_update"] = "state_update"
    map: str
    states: StreamedMapStates
    # Objects that left the map since the last tick; empty on a ``full`` tick,
    # which is authoritative on its own.
    removed_ids: list[str] = []
    full: bool = True
    # Check timing for objects whose state is unchanged — kept out of ``states``
    # so a recheck does not resend the whole object.
    timing: list[ObjectTiming] = []


class TopologyUpdateMessage(BaseModel):
    type: Literal["topology_update"] = "topology_update"
    map: str
    delta: TopologyDelta


# What a client has to be able to handle on the stream.
StreamMessage = StateUpdateMessage | TopologyUpdateMessage
