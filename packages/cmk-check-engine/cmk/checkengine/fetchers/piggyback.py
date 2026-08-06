#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override, Self, TypedDict

from cmk.checkengine.fetcher_abc import DeserializationContext, Fetcher, Mode
from cmk.checkengine.helper_interface import AgentRawData


class PiggybackFetcherParams(TypedDict):
    pass


class PiggybackFetcher(Fetcher[AgentRawData, PiggybackFetcherParams]):
    def __init__(
        self,
    ) -> None:
        super().__init__()

    @override
    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    @override
    def __eq__(self, other: object) -> bool:
        return isinstance(other, PiggybackFetcher)

    @override
    def serialized_params(self) -> PiggybackFetcherParams:
        return {}

    @classmethod
    @override
    def from_params(cls, _params: PiggybackFetcherParams, _ctx: DeserializationContext) -> Self:
        return cls()

    @override
    def open(self) -> None:
        pass

    @override
    def close(self) -> None:
        pass

    @override
    def _fetch_from_io(self, _mode: Mode) -> AgentRawData:
        # The piggybacked data is fetched from disk by the piggyback parser, not here.
        # We still maintain this fetcher for symmetry and to make sure the fetcher
        # processes are fully in charge of which datasources are expected.
        return AgentRawData(b"")
