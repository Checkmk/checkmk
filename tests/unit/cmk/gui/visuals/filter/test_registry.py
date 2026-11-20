#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from typing import override

from cmk.gui.config import RequestCacheConfig
from cmk.gui.visuals.filter import Filter, FilterRegistry
from cmk.gui.visuals.filter.components import FilterComponent
from cmk.web.utils.request_cache import RequestCache


class _StubFilter(Filter):
    @override
    def components(
        self, _request_cache: RequestCache[RequestCacheConfig]
    ) -> Iterable[FilterComponent]:
        return []


def _registry_with_stub_filter() -> FilterRegistry:
    registry = FilterRegistry()
    registry.register(
        _StubFilter(
            ident="stub",
            title="Stub filter",
            sort_index=1,
            info="host",
            htmlvars=["stub"],
            link_columns=[],
        )
    )
    return registry


def test_title_of_a_registered_filter() -> None:
    assert _registry_with_stub_filter().title_of("stub") == "Stub filter"


def test_title_of_an_unknown_filter_is_none() -> None:
    assert _registry_with_stub_filter().title_of("unknown") is None
