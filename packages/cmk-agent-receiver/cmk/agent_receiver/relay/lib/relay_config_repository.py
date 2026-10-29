#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator
from pathlib import Path
from typing import final, Literal

from cmk.agent_receiver.relay.lib.shared_types import RelayID, Serial


@final
class RelayConfigRepository:
    """The relay configs of the activated configurations, as the core's helper config holds them.

    Each activation writes a folder named by its serial; `latest` links to the active one.
    """

    def __init__(self, *, helper_config_dir: Path) -> None:
        self._helper_config_dir = helper_config_dir

    def relay_ids(self, serial: Serial | Literal["latest"] = "latest") -> Iterator[RelayID]:
        for _, dirs, _ in self._relays(serial).walk():
            return (RelayID(d) for d in dirs)
        return iter(())  # The folder does not exist

    def has_config(self, relay_id: RelayID, serial: Serial | Literal["latest"] = "latest") -> bool:
        return self.config_dir(relay_id, serial).exists()

    def config_dir(self, relay_id: RelayID, serial: Serial | Literal["latest"]) -> Path:
        return self._relays(serial) / str(relay_id)

    def _relays(self, serial: Serial | Literal["latest"]) -> Path:
        return self._helper_config_dir / str(serial) / "relays"
