#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, NoReturn

from cmk.utils.type_defs import AgentRawData

from cmk.fetchers import Fetcher, Mode

__all__ = ["NoFetcher"]


class NoFetcher(Fetcher[AgentRawData]):
    def __init__(self) -> None:
        super().__init__(logger=logging.getLogger("cmk.helper.noop"))

    @classmethod
    def _from_json(cls, serialized: object) -> NoFetcher:
        return NoFetcher()

    def to_json(self) -> Mapping[str, Any]:
        return {}

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def _fetch_from_io(self, mode: Mode) -> NoReturn:
        raise TypeError(self)
