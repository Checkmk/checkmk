#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from logging import Logger
from pathlib import Path
from typing import Final, Generic, Protocol, TypeVar

from cmk.utils.plugin_registry import Registry
from cmk.utils.store import load_object_from_file
from cmk.utils.user import UserId

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.pagetypes import (
    all_page_types,
    InstanceId,
    Overridable,
    OverridableInstances,
    OverridableSpec,
)
from cmk.gui.plugins.sidebar.bookmarks import BookmarkList, BookmarkListSpec
from cmk.gui.userdb import load_users

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState

_TOverridable_co = TypeVar("_TOverridable_co", bound=Overridable, covariant=True)


class PagetypeUpdater(Protocol, Generic[_TOverridable_co]):
    @property
    def target_type(self) -> type[_TOverridable_co]:
        ...

    def __call__(
        self, page_dicts: Mapping[InstanceId, dict[str, object]]
    ) -> Mapping[InstanceId, dict[str, object]]:
        ...


class PagetypeUpdaterRegistry(Registry[PagetypeUpdater]):
    def plugin_name(self, instance: PagetypeUpdater) -> str:
        return str(instance)  # not used


pagetype_updater_registry = PagetypeUpdaterRegistry()


class UpdatePagetypes(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        for pagetype in all_page_types().values():
            raw_page_dicts = pagetype.load_raw()
            for updater in pagetype_updater_registry.values():
                if issubclass(pagetype, updater.target_type):
                    raw_page_dicts = updater(raw_page_dicts)

            instances = OverridableInstances[Overridable[OverridableSpec]]()
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


class BookmarkListUpdater:
    def __init__(self) -> None:
        self.target_type: Final = BookmarkList

    def __call__(
        self, page_dicts: Mapping[InstanceId, dict[str, object]]
    ) -> Mapping[InstanceId, dict[str, object]]:
        bookmark_lists_by_instance_id: dict[InstanceId, BookmarkListSpec] = {}
        for user_id in load_users():
            # Don't load the legacy bookmarks when there is already a my_bookmarks list
            if (user_id, "my_bookmarks") in page_dicts:
                continue

            # Also don't load them when the user has at least one bookmark list
            for user_id_bookmarks, _name in page_dicts:
                if user_id == user_id_bookmarks:
                    continue

            # Ensure that the user has a confdir
            if not (user_confdir := LoggedInUser(user_id).confdir):
                continue

            bookmark_lists_by_instance_id.setdefault(
                (user_id, "my_bookmarks"),
                {
                    "title": "My Bookmarks",
                    "public": False,
                    "owner": user_id,
                    "name": "my_bookmarks",
                    "description": "Your personal bookmarks",
                    "default_topic": "My Bookmarks",
                    "bookmarks": [
                        {
                            "title": title,
                            "url": url,
                            "icon": None,
                            "topic": None,
                        }
                        for title, url in self._load_and_delete_legacy_bookmarks(Path(user_confdir))
                    ],
                },
            )

        return page_dicts

    @staticmethod
    def _load_and_delete_legacy_bookmarks(user_confdir: Path) -> list[tuple[str, str]]:
        if not (legacy_path := user_confdir / "bookmarks.mk").exists():
            return []
        legacy_bookmarks = load_object_from_file(legacy_path, default=[])
        legacy_path.unlink()
        return list(legacy_bookmarks)  # make mypy happy


pagetype_updater_registry.register(BookmarkListUpdater())
