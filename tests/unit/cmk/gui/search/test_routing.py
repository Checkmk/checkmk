#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import inspect
from collections.abc import Callable
from typing import get_args, override

import pytest

from cmk.gui.search._routing import CompositePermissionsHandler
from cmk.gui.search.matchers import (
    ABCMatchItemGenerator,
    MatchItemGeneratorRegistry,
    MatchItems,
)
from cmk.gui.utils.roles import UserPermissions
from cmk.shared_typing.unified_search import ProviderName


class _FakeGenerator(ABCMatchItemGenerator):
    @override
    def generate_match_items(self, user_permissions: UserPermissions) -> MatchItems:
        yield from ()

    @staticmethod
    @override
    def is_affected_by_change(change_action_name: str) -> bool:
        return False

    @property
    @override
    def is_localization_dependent(self) -> bool:
        return False


class _FakeHandler:
    def __init__(self, *, may_see: bool = True, visible: bool = True) -> None:
        self._may_see = may_see
        self._visible = visible

    def may_see_category(self, category: str) -> bool:
        return self._may_see

    def get_visibility_check(self, category: str) -> Callable[[str], bool]:
        return lambda _url: self._visible


@pytest.fixture(name="registry")
def fixture_registry() -> MatchItemGeneratorRegistry:
    registry = MatchItemGeneratorRegistry()
    registry.register(_FakeGenerator("hosts", provider="setup"))
    registry.register(_FakeGenerator("customize", provider="customize"))
    return registry


class TestMatchItemGeneratorRegistryProviderFor:
    def test_setup_category_defaults_to_setup(self, registry: MatchItemGeneratorRegistry) -> None:
        assert registry.provider_for("hosts") is ProviderName.setup

    def test_explicit_provider_is_returned(self, registry: MatchItemGeneratorRegistry) -> None:
        assert registry.provider_for("customize") is ProviderName.customize

    def test_unknown_category_returns_none(self, registry: MatchItemGeneratorRegistry) -> None:
        assert registry.provider_for("nope") is None


def test_generator_provider_literal_matches_shared_type_members() -> None:
    provider_param = inspect.signature(ABCMatchItemGenerator.__init__).parameters["provider"]

    value = set(get_args(provider_param.annotation))
    expected = {member.value for member in ProviderName}

    assert value == expected


class TestCompositePermissionsHandler:
    def test_dispatches_may_see_to_provider_handler(
        self, registry: MatchItemGeneratorRegistry
    ) -> None:
        composite = CompositePermissionsHandler(
            registry,
            {
                ProviderName.setup: _FakeHandler(may_see=True),
                ProviderName.customize: _FakeHandler(may_see=False),
            },
        )
        assert composite.may_see_category("hosts") is True
        assert composite.may_see_category("customize") is False

    def test_dispatches_visibility_to_provider_handler(
        self, registry: MatchItemGeneratorRegistry
    ) -> None:
        composite = CompositePermissionsHandler(
            registry,
            {
                ProviderName.setup: _FakeHandler(visible=True),
                ProviderName.customize: _FakeHandler(visible=False),
            },
        )
        assert composite.get_visibility_check("hosts")("url") is True
        assert composite.get_visibility_check("customize")("url") is False

    def test_category_without_handler_is_denied(self, registry: MatchItemGeneratorRegistry) -> None:
        composite = CompositePermissionsHandler(
            registry,
            {ProviderName.setup: _FakeHandler()},
        )
        assert composite.may_see_category("customize") is False
        assert composite.get_visibility_check("customize")("url") is False

    def test_unknown_category_is_denied(self, registry: MatchItemGeneratorRegistry) -> None:
        composite = CompositePermissionsHandler(
            registry,
            {ProviderName.setup: _FakeHandler()},
        )
        assert composite.may_see_category("nope") is False
        assert composite.get_visibility_check("nope")("url") is False
