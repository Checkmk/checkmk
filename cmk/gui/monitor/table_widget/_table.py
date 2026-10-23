#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from cmk.gui.type_defs import FilterName


class InvalidSortError(ValueError):
    pass


class TableCatalog(ABC):
    @property
    @abstractmethod
    def column_ids(self) -> Sequence[str]: ...

    @abstractmethod
    def validate(self, columns: Sequence[str], sort: Sequence[str]) -> None: ...


@dataclass(frozen=True)
class TableRows[R]:
    rows: Sequence[R]
    matched: int
    total: int
    unapplied_filters: Sequence[FilterName]
