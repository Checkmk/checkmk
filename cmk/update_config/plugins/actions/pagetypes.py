#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import Generic, Protocol, TypeVar

from cmk.utils.plugin_registry import Registry
from cmk.utils.user import UserId

from cmk.gui.pagetypes import all_page_types, Overridable, OverridableInstances

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState

TOverridable = TypeVar("TOverridable", bound=Overridable)


class PagetypeUpdater(Protocol, Generic[TOverridable]):
    @property
    def target_type(self) -> type[TOverridable]:
        ...

    def __call__(
        self, instances: OverridableInstances[TOverridable]
    ) -> OverridableInstances[TOverridable]:
        ...


class PagetypeUpdaterRegistry(Registry[PagetypeUpdater]):
    def plugin_name(self, instance: PagetypeUpdater) -> str:
        return str(instance)  # not used


pagetype_updater_registry = PagetypeUpdaterRegistry()


class UpdatePagetypes(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        for pagetype in all_page_types().values():
            for updater in pagetype_updater_registry.values():
                if not issubclass(pagetype, updater.target_type):
                    continue

                instances = updater(pagetype.load())

                for user_id in (
                    user_id
                    for (user_id, name) in instances.instances_dict()
                    if user_id != UserId.builtin()
                ):
                    pagetype.save_user_instances(instances, owner=user_id)


update_action_registry.register(
    UpdatePagetypes(
        name="pagetypes",
        title="Update pagetypes",
        sort_index=120,  # can run whenever
    )
)
