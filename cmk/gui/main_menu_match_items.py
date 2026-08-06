#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable
from typing import Literal, override

from cmk.gui.main_menu import get_main_menu_items_prefixed_by_segment
from cmk.gui.search.matchers import ABCMatchItemGenerator, MatchItem, MatchItems
from cmk.gui.utils.loading_transition import LoadingTransition
from cmk.gui.utils.roles import UserPermissions
from cmk.shared_typing.main_menu import NavItemTopic


class MatchItemGeneratorMainMenu(ABCMatchItemGenerator):
    def __init__(
        self,
        name: str,
        *,
        provider: Literal["customize", "setup"],
        topic_generator: Callable[[UserPermissions], Iterable[NavItemTopic]] | None,
        topic: str | None = None,
    ) -> None:
        super().__init__(name, provider=provider)
        self._topic_generator = topic_generator
        self._topic = topic

    @override
    def generate_match_items(self, user_permissions: UserPermissions) -> MatchItems:
        yield from (
            MatchItem(
                title=main_menu_item.title,
                topic=self._topic or main_menu_topic.title,
                url=main_menu_item.url,
                match_texts=[
                    main_menu_item.title,
                    *(main_menu_item.main_menu_search_terms or []),
                ],
                loading_transition=LoadingTransition(main_menu_item.loading_transition)
                if main_menu_item.loading_transition
                else None,
            )
            for main_menu_topic in (
                self._topic_generator(user_permissions) if self._topic_generator else []
            )
            for main_menu_item in get_main_menu_items_prefixed_by_segment(main_menu_topic)
            if main_menu_item.url
        )

    @staticmethod
    @override
    def is_affected_by_change(change_action_name: str) -> bool:
        return False

    @property
    @override
    def is_localization_dependent(self) -> bool:
        return True
