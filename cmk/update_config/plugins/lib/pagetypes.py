#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from logging import Logger
from typing import Final, override, Protocol

from cmk.ccc.user import UserId
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.logged_in import save_user_file
from cmk.gui.pagetypes import (
    Overridable,
    OverridableInstances,
)
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.pre_actions.utils import (
    ConflictMode,
    continue_per_users_choice,
    Resume,
)
from cmk.update_config.registry import (
    PreUpdateAction,
    UpdateAction,
)

_DEFAULT_CONFLICT_HINT: Final = (
    "It is possible that the errors shown above are due to configurations which were already "
    "invalid before the update. You might be able to fix these elements by opening them in the "
    "UI and checking for errors."
)


def unconverted_file_name(type_name: str) -> str:
    """The file an update action parks a page it could not convert in."""
    return f"user_{type_name}s_unconverted"


class PagetypeUpdater[TOverridable_co: Overridable](Protocol):
    @property
    def target_type(self) -> type[TOverridable_co]: ...
    def update_raw_page_dict(self, page_dict: dict[str, object]) -> dict[str, object]: ...


class UpdatePagetypes[TOverridable_co: Overridable](UpdateAction):
    def __init__(
        self,
        *,
        name: str,
        title: str,
        sort_index: int,
        updater: PagetypeUpdater[TOverridable_co],
        expiry_version: ExpiryVersion = ExpiryVersion.NEVER,
        continue_on_failure: bool = True,
    ):
        super().__init__(
            name=name,
            title=title,
            sort_index=sort_index,
            continue_on_failure=continue_on_failure,
            expiry_version=expiry_version,
        )
        self._updater = updater

    @override
    def __call__(self, logger: Logger) -> None:
        target_type = self._updater.target_type
        raw_page_dicts = target_type.load_raw()

        instances = OverridableInstances[TOverridable_co]()
        unconverted: dict[UserId, dict[str, object]] = {}
        for (user_id, name), raw_page_dict in raw_page_dicts.items():
            try:
                instance = target_type.deserialize(
                    self._updater.update_raw_page_dict(raw_page_dict)
                )
            except Exception:
                logger.exception(
                    "Keeping %(type_name)s %(name)r of user %(user_id)r in its old format,"
                    " because it could not be converted",
                    {"type_name": target_type.type_name(), "name": name, "user_id": user_id},
                )
                unconverted.setdefault(user_id, {})[name] = raw_page_dict
                continue
            instances.add_instance((user_id, name), instance)

        user_permissions = UserPermissions.from_config(active_config, permission_registry)
        for user_id in {
            user_id for user_id, _name in raw_page_dicts if user_id != UserId.builtin()
        }:
            target_type.save_user_instances(instances, user_permissions, owner=user_id)

        # A graph that survives here is one the operator forced the update past. It stays readable
        # in its own file, which the pagetype never loads, rather than being dropped.
        for user_id, page_dicts in unconverted.items():
            save_user_file(unconverted_file_name(target_type.type_name()), page_dicts, user_id)


class PreUpdatePagetypes[TOverridable_co: Overridable](PreUpdateAction):
    def __init__(
        self,
        *,
        name: str,
        title: str,
        sort_index: int,
        updater: PagetypeUpdater[TOverridable_co],
        element_name: str,
        conflict_hint: str = _DEFAULT_CONFLICT_HINT,
        expiry_version: ExpiryVersion = ExpiryVersion.NEVER,
    ) -> None:
        super().__init__(
            name=name,
            title=title,
            sort_index=sort_index,
            expiry_version=expiry_version,
        )
        self._updater = updater
        self._element_name_for_logging = element_name
        self._conflict_hint = conflict_hint

    @override
    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        encountered_errors = False

        for (user_id, element_id), raw_page_dict in self._updater.target_type.load_raw().items():
            try:
                updated_raw_page_dict = self._updater.update_raw_page_dict(raw_page_dict)
            except Exception:
                encountered_errors = True
                logger.exception(
                    "Error while updating %(element_name)s. ID: %(element_id)s. Owner: %(owner)s.",
                    {
                        "element_name": self._element_name_for_logging,
                        "element_id": element_id,
                        "owner": user_id,
                    },
                )
                continue
            try:
                self._updater.target_type.deserialize(updated_raw_page_dict)
            except Exception:
                encountered_errors = True
                logger.exception(
                    "Error while deserializing updated %(element_name)s. "
                    "ID: %(element_id)s. Owner: %(owner)s.",
                    {
                        "element_name": self._element_name_for_logging,
                        "element_id": element_id,
                        "owner": user_id,
                    },
                )

        if (
            encountered_errors
            and _continue_per_users_choice(conflict_mode, self._conflict_hint).is_abort()
        ):
            raise MKUserError(None, f"{self._element_name_for_logging} errors")


def _continue_per_users_choice(conflict_mode: ConflictMode, conflict_hint: str) -> Resume:
    match conflict_mode:
        case ConflictMode.FORCE:
            return Resume.UPDATE
        case ConflictMode.ABORT:
            return Resume.ABORT
        case ConflictMode.ASK:
            return continue_per_users_choice(
                "You can abort the update process (A) or continue (c) the update. "
                "Continuing might render your site in an invalid state. "
                f"{conflict_hint} "
                "Abort update? [A/c]\n"
            )
