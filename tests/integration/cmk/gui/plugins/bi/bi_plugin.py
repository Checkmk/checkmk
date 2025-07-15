#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.bi.lib import ABCBISearch, ABCBISearcher, bi_search_registry, SearchKind
from cmk.bi.schema import Schema
from cmk.utils.macros import MacroMapping


@bi_search_registry.register
class TestBISearch(ABCBISearch):
    @classmethod
    def kind(cls) -> SearchKind:
        return "test"  # type: ignore[return-value]

    @classmethod
    def schema(cls) -> type[Schema]:
        raise NotImplementedError()

    def serialize(self):
        return {
            "type": self.kind(),
            "conditions": {},
        }

    def execute(self, macros: MacroMapping, bi_searcher: ABCBISearcher) -> list[dict]:
        return []
