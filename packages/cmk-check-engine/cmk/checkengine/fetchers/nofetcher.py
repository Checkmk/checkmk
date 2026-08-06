#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import enum
from typing import Final, NoReturn, override, Self, TypedDict

from cmk.checkengine.fetcher_abc import DeserializationContext, Fetcher, FetcherError, Mode
from cmk.checkengine.helper_interface import AgentRawData

__all__ = ["NoFetcherError", "NoFetcher"]


class NoFetcherParams(TypedDict):
    canned: str


@enum.unique
class NoFetcherError(enum.Enum):
    """Enumeration of possible error messages

    The messages are visible in the UI and should be user friendly.
    """

    NO_FETCHER = "host configuration requires a datasource but none configured"
    MISSING_IP = "Failed to lookup IP address and no explicit IP address configured"


class NoFetcher(Fetcher[AgentRawData, NoFetcherParams]):
    def __init__(self, /, canned: NoFetcherError) -> None:
        super().__init__()
        self.canned: Final = canned

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NoFetcher):
            return False
        return self.canned == other.canned

    @override
    def serialized_params(self) -> NoFetcherParams:
        return {"canned": self.canned.name}

    @classmethod
    @override
    def from_params(cls, params: NoFetcherParams, _ctx: DeserializationContext) -> Self:
        return cls(NoFetcherError[params["canned"]])

    @override
    def open(self) -> None:
        pass

    @override
    def close(self) -> None:
        pass

    @override
    def _fetch_from_io(self, _mode: Mode) -> NoReturn:
        raise FetcherError(self.canned.value)
