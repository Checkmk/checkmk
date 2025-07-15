#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import enum
from typing import Final, NoReturn

from cmk.ccc.exceptions import MKFetcherError
from cmk.utils.agentdatatype import AgentRawData

from ._abstract import Fetcher, Mode

__all__ = ["NoFetcherError", "NoFetcher"]


@enum.unique
class NoFetcherError(enum.Enum):
    """Enumeration of possible error messages

    The messages are visible in the UI and should be user friendly.
    """

    NO_FETCHER = "host configuration requires a datasource but none configured"
    MISSING_IP = "Failed to lookup IP address and no explicit IP address configured"


class NoFetcher(Fetcher[AgentRawData]):
    def __init__(self, /, canned: NoFetcherError) -> None:
        super().__init__()
        self.canned: Final = canned

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NoFetcher):
            return False
        return self.canned == other.canned

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def _fetch_from_io(self, mode: Mode) -> NoReturn:
        raise MKFetcherError(self.canned.value)
