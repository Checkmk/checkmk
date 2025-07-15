#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import Final, Generic, override, Protocol, TypeVar

from cmk.ccc.user import UserId

from cmk.gui.pagetypes import (
    Overridable,
    OverridableInstances,
    PagetypeTopics,
)

from cmk.update_config.registry import update_action_registry, UpdateAction

_TOverridable_co = TypeVar("_TOverridable_co", bound=Overridable, covariant=True)


class PagetypeUpdater(Protocol, Generic[_TOverridable_co]):
    @property
    def target_type(self) -> type[_TOverridable_co]: ...

    def update_raw_page_dict(self, page_dict: dict[str, object]) -> dict[str, object]: ...


class UpdatePagetypes(UpdateAction, Generic[_TOverridable_co]):
    def __init__(
        self,
        *,
        name: str,
        title: str,
        sort_index: int,
        updater: PagetypeUpdater[_TOverridable_co],
        continue_on_failure: bool = True,
    ):
        super().__init__(
            name=name,
            title=title,
            sort_index=sort_index,
            continue_on_failure=continue_on_failure,
        )
        self._updater = updater

    @override
    def __call__(self, logger: Logger) -> None:
        updated_raw_page_dicts = {
            instance_id: self._updater.update_raw_page_dict(raw_page_dict)
            for instance_id, raw_page_dict in self._updater.target_type.load_raw().items()
        }

        instances = OverridableInstances[_TOverridable_co]()
        for (user_id, name), raw_page_dict in updated_raw_page_dicts.items():
            instances.add_instance(
                (user_id, name), self._updater.target_type.deserialize(raw_page_dict)
            )

        for user_id in (
            user_id for (user_id, name) in instances.instances_dict() if user_id != UserId.builtin()
        ):
            self._updater.target_type.save_user_instances(instances, owner=user_id)


class PagetypeTopicsUpdater:
    def __init__(self) -> None:
        self.target_type: Final = PagetypeTopics

    def update_raw_page_dict(self, page_dict: dict[str, object]) -> dict[str, object]:
        return page_dict | {
            "icon_name": (
                page_dict["icon_name"]
                # transparent icon
                or "trans"
            )
        }


update_action_registry.register(
    UpdatePagetypes(
        name="pagetype_topics",
        title="Topics",
        sort_index=120,  # can run whenever
        updater=PagetypeTopicsUpdater(),
    )
)
