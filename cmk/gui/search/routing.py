#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.gui.search.match_items import MatchItemGeneratorRegistry
from cmk.gui.search.type_defs import SearchPermissionsHandler, VisibilityCheck
from cmk.shared_typing.unified_search import ProviderName


class CompositePermissionsHandler:
    def __init__(
        self,
        registry: MatchItemGeneratorRegistry,
        handlers: Mapping[ProviderName, SearchPermissionsHandler],
    ) -> None:
        self._registry = registry
        self._handlers = handlers

    def may_see_category(self, category: str) -> bool:
        handler = self._handler_for(category)
        return handler.may_see_category(category) if handler else False

    def get_visibility_check(self, category: str) -> VisibilityCheck:
        handler = self._handler_for(category)
        return handler.get_visibility_check(category) if handler else (lambda _url: False)

    def _handler_for(self, category: str) -> SearchPermissionsHandler | None:
        if (provider := self._registry.provider_for(category)) is None:
            return None
        return self._handlers.get(provider)
