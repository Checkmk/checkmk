#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from logging import Logger
from typing import Final, Generic, Protocol, TypeVar

from cmk.ccc.plugin_registry import Registry

from cmk.utils.user import UserId

from cmk.gui.pagetypes import (
    all_page_types,
    InstanceId,
    Overridable,
    OverridableConfig,
    OverridableInstances,
    PagetypeTopics,
)

from cmk.update_config.registry import update_action_registry, UpdateAction

_TOverridable_co = TypeVar("_TOverridable_co", bound=Overridable, covariant=True)


class PagetypeUpdater(Protocol, Generic[_TOverridable_co]):
    @property
    def target_type(self) -> type[_TOverridable_co]: ...

    def __call__(
        self, page_dicts: Mapping[InstanceId, dict[str, object]]
    ) -> Mapping[InstanceId, dict[str, object]]: ...


class PagetypeUpdaterRegistry(Registry[PagetypeUpdater]):
    def plugin_name(self, instance: PagetypeUpdater) -> str:
        return str(instance)  # not used


pagetype_updater_registry = PagetypeUpdaterRegistry()


class UpdatePagetypes(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        for pagetype in all_page_types().values():
            raw_page_dicts = pagetype.load_raw()
            for updater in pagetype_updater_registry.values():
                if issubclass(pagetype, updater.target_type):
                    raw_page_dicts = updater(raw_page_dicts)

            instances = OverridableInstances[Overridable[OverridableConfig]]()
            for (user_id, name), raw_page_dict in raw_page_dicts.items():
                instances.add_instance((user_id, name), pagetype.deserialize(raw_page_dict))

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


class PagetypeTopicsUpdater:
    def __init__(self) -> None:
        self.target_type: Final = PagetypeTopics

    def __call__(
        self, page_dicts: Mapping[InstanceId, dict[str, object]]
    ) -> Mapping[InstanceId, dict[str, object]]:
        return {
            instance_id: page_dict
            | {
                "icon_name": (
                    icon_name
                    if (icon_name := page_dict["icon_name"])
                    # transparent icon
                    else "trans"
                )
            }
            for instance_id, page_dict in page_dicts.items()
        }


pagetype_updater_registry.register(PagetypeTopicsUpdater())
