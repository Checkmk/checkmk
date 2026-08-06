#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

import pytest

from cmk.gui.search.matchers import ABCMatchItemGenerator, MatchItemGeneratorRegistry, MatchItems
from cmk.gui.utils.roles import UserPermissions
from cmk.shared_typing.unified_search import ProviderName


class TestCategoriesFor:
    @pytest.fixture
    def registry(self) -> MatchItemGeneratorRegistry:
        registry = MatchItemGeneratorRegistry()
        registry.register(_FakeGenerator("hosts", provider="setup"))
        registry.register(_FakeGenerator("notifications", provider="setup"))
        registry.register(_FakeGenerator("views", provider="customize"))
        registry.register(_FakeGenerator("dashboards", provider="customize"))
        return registry

    def test_returns_correct_categories_for_setup(
        self, registry: MatchItemGeneratorRegistry
    ) -> None:
        assert registry.categories_for(ProviderName.setup) == {"hosts", "notifications"}

    def test_returns_correct_categories_for_customize(
        self, registry: MatchItemGeneratorRegistry
    ) -> None:
        assert registry.categories_for(ProviderName.customize) == {"views", "dashboards"}

    def test_result_is_cached(self, registry: MatchItemGeneratorRegistry) -> None:
        first_call = registry.categories_for(ProviderName.setup)
        second_call = registry.categories_for(ProviderName.setup)
        assert first_call is second_call


class _FakeGenerator(ABCMatchItemGenerator):
    @override
    def generate_match_items(self, user_permissions: UserPermissions) -> MatchItems:
        return iter([])

    @staticmethod
    @override
    def is_affected_by_change(change_action_name: str) -> bool:
        return False

    @property
    @override
    def is_localization_dependent(self) -> bool:
        return False
