#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import Generic, override, Protocol, TypeVar

from cmk.ccc.user import UserId

from cmk.gui.exceptions import MKUserError
from cmk.gui.pagetypes import (
    Overridable,
    OverridableInstances,
)

from cmk.update_config.plugins.pre_actions.utils import (
    ConflictMode,
    continue_per_users_choice,
    Resume,
)
from cmk.update_config.registry import (
    PreUpdateAction,
    UpdateAction,
)

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
            name=name, title=title, sort_index=sort_index, continue_on_failure=continue_on_failure
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


class PreUpdatePagetypes(PreUpdateAction, Generic[_TOverridable_co]):
    def __init__(
        self,
        *,
        name: str,
        title: str,
        sort_index: int,
        updater: PagetypeUpdater[_TOverridable_co],
        element_name: str,
    ) -> None:
        super().__init__(
            name=name,
            title=title,
            sort_index=sort_index,
        )
        self._updater = updater
        self._element_name_for_logging = element_name

    @override
    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        encountered_update_errors = False
        encountered_deserialization_errors = False

        for (user_id, element_id), raw_page_dict in self._updater.target_type.load_raw().items():
            try:
                updated_raw_page_dict = self._updater.update_raw_page_dict(raw_page_dict)
            except Exception as exception:
                encountered_update_errors = True
                logger.error(
                    f"Error while updating {self._element_name_for_logging}. ID: {element_id}. Owner: {user_id}. Error message:\n{exception}\n\n"
                )
            try:
                self._updater.target_type.deserialize(updated_raw_page_dict)
            except Exception as exception:
                encountered_deserialization_errors = True
                logger.error(
                    f"Error while deserializing updated {self._element_name_for_logging}. ID: {element_id}. Owner: {user_id}. Error message:\n{exception}\n\n"
                )

        if encountered_update_errors or encountered_deserialization_errors:
            if _continue_per_users_choice(conflict_mode).is_abort():
                raise MKUserError(None, f"{self._element_name_for_logging} errors")


def _continue_per_users_choice(conflict_mode: ConflictMode) -> Resume:
    match conflict_mode:
        case ConflictMode.FORCE:
            return Resume.UPDATE
        case ConflictMode.ABORT:
            return Resume.ABORT
        case ConflictMode.INSTALL | ConflictMode.KEEP_OLD:
            return Resume.ABORT
        case ConflictMode.ASK:
            return continue_per_users_choice(
                "You can abort the update process (A) or continue (c) the update. "
                "Continuing might render your site in an invalid state. "
                "It is possible that the errors shown above are due to configurations which were already invalid before the update. "
                "You might be able to fix these elements by opening them in the UI and checking for errors. "
                "Abort update? [A/c]\n"
            )
