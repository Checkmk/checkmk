#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import enum
import logging
from collections.abc import Mapping
from typing import Final, NoReturn

from cmk.utils.exceptions import MKFetcherError
from cmk.utils.type_defs import AgentRawData

from cmk.fetchers import Fetcher, Mode

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
        super().__init__(logger=logging.getLogger("cmk.helper.noop"))
        self._canned: Final = canned

    @classmethod
    def _from_json(cls, serialized: Mapping[str, str]) -> NoFetcher:
        return NoFetcher(NoFetcherError[serialized["canned"]])

    def to_json(self) -> Mapping[str, str]:
        return {"canned": self._canned.name}

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def _fetch_from_io(self, mode: Mode) -> NoReturn:
        raise MKFetcherError(self._canned.value)
