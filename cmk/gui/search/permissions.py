#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass
from typing import override, Protocol

from cmk.ccc.plugin_registry import Registry
from cmk.gui.pages import PageContext
from cmk.shared_typing.unified_search import ProviderName

type VisibilityCheck = Callable[[str], bool]


class SearchPermissionsHandler(Protocol):
    def may_see_category(self, category: str) -> bool: ...

    def get_visibility_check(self, category: str) -> VisibilityCheck: ...


@dataclass(frozen=True)
class SearchPermissionsHandlerFactory:
    provider: ProviderName
    build: Callable[[PageContext], SearchPermissionsHandler]


class SearchPermissionsHandlerRegistry(Registry[SearchPermissionsHandlerFactory]):
    @override
    def plugin_name(self, instance: SearchPermissionsHandlerFactory) -> str:
        return instance.provider


search_permissions_handler_registry = SearchPermissionsHandlerRegistry()
