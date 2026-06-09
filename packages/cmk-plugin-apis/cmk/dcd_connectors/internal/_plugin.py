#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from ._connector_object import ConnectorObject
from ._types import ChangeDirective, GlobalIdent


class PhaseStep(Protocol):
    """Handle provided by the daemon to report phase progress."""

    def finish(self, message: str) -> None: ...
    def abort(self, message: str) -> None: ...


class ConnectorContext(Protocol):
    """Context provided by the daemon to connectors."""

    @property
    def logger(self) -> logging.Logger: ...
    @property
    def connection_id(self) -> str: ...
    @property
    def site_id(self) -> str: ...
    def global_ident(self) -> GlobalIdent: ...
    def get_raw_config(self) -> dict: ...  # type: ignore[type-arg]
    def get_omd_root(self) -> Path: ...
    def get_initialization_time(self) -> int: ...


@dataclasses.dataclass(frozen=True)
class SiteChanges[HostT: str]:
    """Result of a connector's site change computation.

    The daemon wraps this into a ``ChangeBatch`` with metadata.
    """

    directive: ChangeDirective[HostT]
    discover: bool = True


class Connector[HostT: str](Protocol):
    """Protocol that connectors implement.

    Instances are created by the factory in ``ConnectorSpec.create_connector``.
    The daemon calls these methods during the synchronization loop.
    """

    def execution_interval(self) -> float:
        """Number of seconds between executions."""
        ...

    def phase1_title(self) -> str:
        """Human-readable title for the phase 1 execution step."""
        ...

    def execute_phase1(self, step: PhaseStep) -> ConnectorObject[HostT]:
        """Execute phase 1: collect data and return a ConnectorObject."""
        ...

    def get_site_changes(
        self, hosts: Sequence[HostT], connector_object: ConnectorObject[HostT]
    ) -> SiteChanges[HostT] | None:
        """Given the hosts extracted from the phase 1 result, return site changes.

        Return ``None`` to skip site changes for this cycle.
        The ``hosts`` parameter contains the host names extracted from
        ``connector_object`` by the daemon. The ``connector_object`` is provided
        for access to additional data beyond hosts.
        """
        ...

    def load_config(self) -> None:
        """Reload configuration from the config server."""
        ...
