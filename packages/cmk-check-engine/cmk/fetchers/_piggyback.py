#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.helper_interface import AgentRawData

from ._abstract import Fetcher, Mode


class PiggybackFetcher(Fetcher[AgentRawData]):
    def __init__(
        self,
    ) -> None:
        super().__init__()

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PiggybackFetcher)

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def _fetch_from_io(self, _mode: Mode) -> AgentRawData:
        # The piggybacked data is fetched from disk by the piggyback parser, not here.
        # We still maintain this fetcher for symmetry and to make sure the fetcher
        # processes are fully in charge of which datasources are expected.
        return AgentRawData(b"")
