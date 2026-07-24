#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The wire format of the ``create-diagnostics-dump-v2`` automation

The selection is transported as exactly one argument, a JSON object. It
crosses site boundaries in distributed setups and must stay stable across
versions.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, kw_only=True)
class DumpSelection:
    """The resolved selection of a diagnostics dump: plug-in names + the host field"""

    plugins: Sequence[str]
    checkmk_server_host: str = ""

    def serialize(self) -> str:
        """Serialize for the automation call

        >>> DumpSelection(plugins=["general_info"], checkmk_server_host="cmkserver").serialize()
        '{"v": 1, "plugins": ["general_info"], "checkmk_server_host": "cmkserver"}'
        """
        return json.dumps(
            {
                "v": 1,
                "plugins": list(self.plugins),
                "checkmk_server_host": self.checkmk_server_host,
            }
        )

    @classmethod
    def deserialize(cls, raw: str) -> Self:
        """Deserialize an automation argument

        Raises:
            ValueError: if the argument is not a valid v1 selection.
        """
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid diagnostics dump selection: {e}") from e
        if not isinstance(data, dict) or data.get("v") != 1:
            raise ValueError("Invalid diagnostics dump selection: not a v1 selection")
        plugins = data.get("plugins", [])
        checkmk_server_host = data.get("checkmk_server_host", "")
        if not (
            isinstance(plugins, list)
            and all(isinstance(p, str) for p in plugins)
            and isinstance(checkmk_server_host, str)
        ):
            raise ValueError("Invalid diagnostics dump selection: malformed fields")
        return cls(plugins=plugins, checkmk_server_host=checkmk_server_host)
