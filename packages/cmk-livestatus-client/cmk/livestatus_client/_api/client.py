#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from enum import Enum
from typing import Any

from cmk.ccc.site import SiteId
from cmk.livestatus_client._api.commands import Command
from cmk.livestatus_client._connection import lqencode, MultiSiteConnection, SingleSiteConnection


class LivestatusClient:
    def __init__(self, connection: SingleSiteConnection | MultiSiteConnection) -> None:
        self._connection = connection

    def command(self, command: Command, site: SiteId | None = None) -> None:
        self._connection.command(self._serialize_command(command), site)

    @staticmethod
    def _serialize_command(command: Command) -> str:
        def _serialize_type(value: Any) -> str:
            if value is None:
                return ""

            if isinstance(value, str):
                return lqencode(value)
            if isinstance(value, bool):
                return str(int(value))
            if isinstance(value, int):
                return str(value)
            if isinstance(value, datetime):
                return str(int(value.timestamp()))
            if isinstance(value, list) and all(isinstance(v, int) for v in value):
                return ",".join(map(str, value))
            if isinstance(value, Enum):
                return str(value.value)

            raise TypeError(f"Unexpected type in serialization: {type(value)}")

        serialized_args = ";".join(map(_serialize_type, command.args()))
        return f"{command.name()};{serialized_args}"
