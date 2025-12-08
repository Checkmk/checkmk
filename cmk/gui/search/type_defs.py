#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from typing import Protocol

from cmk.shared_typing.unified_search import (
    UnifiedSearchResultItem,
)


class SearchEngine(Protocol):
    def search(self, query: str) -> Iterable[UnifiedSearchResultItem]: ...
