#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator
from pathlib import Path
from typing import final

from cmk.agent_receiver.relay.lib.shared_types import RelayID


@final
class RelayConfigRepository:
    """The relay configs of the activated configuration, as the core's helper config holds them."""

    def __init__(self, *, helper_config_dir: Path) -> None:
        self._latest = helper_config_dir / "latest/relays"

    def relay_ids(self) -> Iterator[RelayID]:
        for _, dirs, _ in self._latest.walk():
            return (RelayID(d) for d in dirs)
        return iter(())  # The folder does not exist

    def has_config(self, relay_id: RelayID) -> bool:
        return (self._latest / str(relay_id)).exists()
