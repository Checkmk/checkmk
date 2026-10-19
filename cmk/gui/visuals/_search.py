#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import override

from cmk.ccc.user import UserId
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext
from cmk.gui.search.matchers import (
    ABCMatchItemGenerator,
    MatchItem,
    MatchItemConfig,
    MatchItemGeneratorRegistry,
    MatchItems,
)
from cmk.gui.search.permissions import (
    CategoryPermissionsHandlerFactory,
    CategoryPermissionsHandlerRegistry,
    VisibilityCheck,
)
from cmk.gui.type_defs import Visual, VisualName, VisualTypeName
from cmk.gui.utils.roles import UserPermissions
from cmk.web.utils.speaklater import LazyString

from ._store import available_by_owner, visuals_saved_change_action
from ._title import visual_title_without_context

type AllVisuals = Mapping[tuple[UserId, VisualName], Visual]


@dataclass(frozen=True)
class BuiltinVisualsSearch:
    what: VisualTypeName
    topic: LazyString
    load_all: Callable[[], AllVisuals]
    url: Callable[[VisualName], str]

    @property
    def category(self) -> str:
        return f"builtin_{self.what}"

    def register(
        self,
        match_item_generator_registry: MatchItemGeneratorRegistry,
        category_permissions_handler_registry: CategoryPermissionsHandlerRegistry,
    ) -> None:
        match_item_generator_registry.register(BuiltinVisualsMatchItemGenerator(self))
        category_permissions_handler_registry.register(
            CategoryPermissionsHandlerFactory(
                category=self.category,
                build=self.build_permissions_handler,
            )
        )

    def build_permissions_handler(self, ctx: PageContext) -> BuiltinVisualsPermissionsHandler:
        return BuiltinVisualsPermissionsHandler(
            self,
            ctx.user_permissions,
        )

    def builtin_visuals(self) -> Mapping[VisualName, Visual]:
        return {
            name: visual
            for (owner, name), visual in self.load_all().items()
            if owner == UserId.builtin()
        }


class BuiltinVisualsMatchItemGenerator(ABCMatchItemGenerator):
    def __init__(self, search: BuiltinVisualsSearch) -> None:
        super().__init__(search.category, provider="customize")
        self._search = search

    @override
    def generate_match_items(
        self, user_permissions: UserPermissions, _config: MatchItemConfig
    ) -> MatchItems:
        for name, visual in self._search.builtin_visuals().items():
            title = visual_title_without_context(visual, visual["context"])
            yield MatchItem(
                title=title,
                topic=str(self._search.topic),
                url=self._search.url(name),
                match_texts=[title, name, *visual["main_menu_search_terms"]],
            )

    @staticmethod
    @override
    def is_affected_by_change(change_action_name: str) -> bool:
        return False

    @property
    @override
    def is_localization_dependent(self) -> bool:
        return True


class BuiltinVisualsPermissionsHandler:
    def __init__(self, search: BuiltinVisualsSearch, user_permissions: UserPermissions) -> None:
        self._search = search
        self._user_permissions = user_permissions

    def may_see_category(self, category: str) -> bool:  # noqa: ARG002
        return user.may(f"general.edit_{self._search.what}")

    def get_visibility_check(self, category: str) -> VisibilityCheck:  # noqa: ARG002
        visible_urls = {
            self._search.url(name)
            for name, visuals_by_owner in available_by_owner(
                self._search.what, self._search.load_all(), self._user_permissions
            ).items()
            if UserId.builtin() in visuals_by_owner
        }
        return lambda url: url in visible_urls


@dataclass(frozen=True)
class CustomVisualsSearch:
    what: VisualTypeName
    topic: LazyString
    load_all: Callable[[], AllVisuals]
    url: Callable[[VisualName, UserId], str]

    @property
    def category(self) -> str:
        return f"custom_{self.what}"

    def register(
        self,
        match_item_generator_registry: MatchItemGeneratorRegistry,
        category_permissions_handler_registry: CategoryPermissionsHandlerRegistry,
    ) -> None:
        match_item_generator_registry.register(CustomVisualsMatchItemGenerator(self))
        category_permissions_handler_registry.register(
            CategoryPermissionsHandlerFactory(
                category=self.category,
                build=self.build_permissions_handler,
            )
        )

    def build_permissions_handler(self, ctx: PageContext) -> CustomVisualsPermissionsHandler:  # noqa: ARG002
        return CustomVisualsPermissionsHandler(self)

    def custom_visuals(self) -> Mapping[tuple[UserId, VisualName], Visual]:
        return {
            (owner, name): visual
            for (owner, name), visual in self.load_all().items()
            if owner != UserId.builtin() and not visual["packaged"]
        }


class CustomVisualsMatchItemGenerator(ABCMatchItemGenerator):
    def __init__(self, search: CustomVisualsSearch) -> None:
        super().__init__(search.category, provider="customize")
        self._search = search

    @override
    def generate_match_items(
        self, user_permissions: UserPermissions, _config: MatchItemConfig
    ) -> MatchItems:
        for (owner, name), visual in self._search.custom_visuals().items():
            title = visual_title_without_context(visual, visual["context"])
            yield MatchItem(
                title=title,
                topic=str(self._search.topic),
                url=self._search.url(name, owner),
                match_texts=[title, name, *visual["main_menu_search_terms"]],
            )

    @override
    def is_affected_by_change(self, change_action_name: str) -> bool:
        return change_action_name in (visuals_saved_change_action(self._search.what), "edit-users")

    @property
    @override
    def is_localization_dependent(self) -> bool:
        return True


class CustomVisualsPermissionsHandler:
    def __init__(self, search: CustomVisualsSearch) -> None:
        self._search = search

    def may_see_category(self, category: str) -> bool:  # noqa: ARG002
        return user.may(f"general.edit_{self._search.what}")

    def get_visibility_check(self, category: str) -> VisibilityCheck:  # noqa: ARG002
        may_edit_foreign = user.may(f"general.edit_foreign_{self._search.what}")
        visible_urls = {
            self._search.url(name, owner)
            for owner, name in self._search.custom_visuals()
            if owner == user.id or may_edit_foreign
        }
        return lambda url: url in visible_urls
