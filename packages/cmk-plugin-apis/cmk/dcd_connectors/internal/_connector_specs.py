#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass

from ._connector_object import ConnectorObject
from ._plugin import Connector, ConnectorContext


@dataclass(frozen=True)
class ConnectorSpec[HostT: str]:
    """Specification of a DCD connector.

    Instances of this class will only be picked up by Checkmk if their names
    start with ``connector_``.

    The ``name`` must be unique across all connectors and must match the
    corresponding :class:`ConnectorParametersSpec` name.
    """

    name: str
    create_connector: Callable[[ConnectorContext], Connector[HostT]]
    connector_object_class: type[ConnectorObject[HostT]]
