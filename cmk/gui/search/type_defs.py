#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable
from typing import Protocol

from cmk.shared_typing.unified_search import UnifiedSearchResultItem

type VisibilityCheck = Callable[[str], bool]


class SearchEngine(Protocol):
    def search(self, query: str) -> Iterable[UnifiedSearchResultItem]: ...


class SearchPermissionsHandler(Protocol):
    def may_see_category(self, category: str) -> bool: ...

    def get_visibility_check(self, category: str) -> VisibilityCheck: ...
