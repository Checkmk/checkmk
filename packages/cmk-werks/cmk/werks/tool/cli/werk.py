#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from pathlib import Path
from typing import NamedTuple, override

from ..parse import WerkV2ParseResult, WerkV3ParseResult


class WerkId:
    __slots__ = ("__id",)

    def __init__(self, id: int):  # noqa: A002
        self.__id = id

    @override
    def __repr__(self) -> str:
        return f"<WerkId {self.__id:0>5}>"

    @override
    def __str__(self) -> str:
        return f"{self.__id:0>5}"

    @property
    def id(self) -> int:
        return self.__id

    @override
    def __eq__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return self.id == other.id
        return False

    @override
    def __hash__(self) -> int:
        return hash(self.__id)


class Werk(NamedTuple):
    path: Path
    id: WerkId
    content: WerkV2ParseResult | WerkV3ParseResult

    @property
    def date(self) -> datetime.datetime:
        return datetime.datetime.fromisoformat(self.content.metadata["date"])
