#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.shared_typing.unified_search import ProviderName

from .matchers import MatchItemGeneratorRegistry
from .permissions import SearchPermissionsHandler, VisibilityCheck


class CompositePermissionsHandler:
    def __init__(
        self,
        registry: MatchItemGeneratorRegistry,
        handlers: Mapping[ProviderName, SearchPermissionsHandler],
        category_handlers: Mapping[str, SearchPermissionsHandler] | None = None,
    ) -> None:
        provider_handlers = {
            category: handler
            for category in registry
            if (provider := registry.provider_for(category)) is not None
            and (handler := handlers.get(provider)) is not None
        }
        self._handlers: Mapping[str, SearchPermissionsHandler] = provider_handlers | {
            category: handler
            for category, handler in (category_handlers or {}).items()
            if category in registry
        }

    def may_see_category(self, category: str) -> bool:
        handler = self._handlers.get(category)
        return handler.may_see_category(category) if handler is not None else False

    def get_visibility_check(self, category: str) -> VisibilityCheck:
        handler = self._handlers.get(category)
        return (
            handler.get_visibility_check(category) if handler is not None else (lambda _url: False)
        )
