#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from typing import cast

from cmk.utils.notify_types import (
    EventRule,
)
from cmk.utils.paths import check_mk_config_dir

from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.notifications import (
    NotificationRuleConfigFile,
)

from cmk.rulesets.v1 import Message
from cmk.rulesets.v1.form_specs.validators import EmailAddress as ValidateEmailAddress
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.update_config.plugins.pre_actions.utils import (
    ConflictMode,
    continue_per_users_choice,
    Resume,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction

type LegacyParameter = dict[str, str] | None


class PreMigrateHtmlEmail(PreUpdateAction):
    """
    In version 2.0 'from' option in HTML email parameters changed from str to dict.
    This migration makes sure, that the update to 2.4 will not break in case an
    old 'from' entry is still present
    """

    def __init__(self, name: str, title: str, sort_index: int) -> None:
        super().__init__(name=name, title=title, sort_index=sort_index)
        self._notifications_mk_path: Path = Path(check_mk_config_dir, "wato/notifications.mk")

    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        notification_rules = NotificationRuleConfigFile().load_for_reading()
        notification_rule_params = (rule["notify_plugin"][1] for rule in notification_rules)
        if all(params is None or isinstance(params, str) for params in notification_rule_params):
            logger.debug("       Already migrated")
            return

        updated_notification_rules: list[EventRule] = []
        for nr, rule in enumerate(notification_rules):
            method = rule["notify_plugin"][0]
            if method != "mail":
                updated_notification_rules.append(rule)
                continue

            parameter = cast(LegacyParameter, rule["notify_plugin"][1])
            if parameter is None:
                updated_notification_rules.append(rule)
                continue

            if "from" not in parameter:
                updated_notification_rules.append(rule)
                continue

            from_value = parameter["from"]
            if isinstance(from_value, dict):
                updated_notification_rules.append(rule)
                continue

            validator = ValidateEmailAddress(error_msg=Message("Invalid email address."))
            try:
                validator(from_value)
            except ValidationError as e:
                error_messages = [
                    "WARNING: Invalid notification rule configuration detected",
                    f"Rule nr.: {nr}",
                    f'Description: {rule["description"]}',
                    f"Invalid value: '{from_value}'",
                    f"Exception: {e}\n",
                ]
                add_info = _additional_info()
                logger.error("\n".join(error_messages + add_info.messages))
                if _continue_on_invalid_from(conflict_mode).is_abort():
                    raise MKUserError(None, "invalid email address")

            parameter["from"] = {"address": from_value}  # type: ignore[assignment]
            rule["notify_plugin"] = (method, parameter)  # type: ignore[typeddict-item]
            logger.debug(f"       Migrated rule nr #{nr}%d with HTML email 'from' parameter")
            updated_notification_rules.append(rule)

        NotificationRuleConfigFile().save(updated_notification_rules)
        logger.debug("       Saved migrated notification rules")


def _continue_on_invalid_from(conflict_mode: ConflictMode) -> Resume:
    match conflict_mode:
        case ConflictMode.FORCE:
            return Resume.UPDATE
        case ConflictMode.ABORT:
            return Resume.ABORT
        case ConflictMode.INSTALL | ConflictMode.KEEP_OLD:
            return Resume.UPDATE
        case ConflictMode.ASK:
            return continue_per_users_choice(
                "You can abort the update process (A) or continue (c) the update. Abort update? [A/c]\n"
            )


@dataclass(frozen=True, kw_only=True)
class _AdditionalInfo:
    messages: list[str]


def _additional_info() -> _AdditionalInfo:
    return _AdditionalInfo(
        messages=[
            "Note:",
            (
                "Continuing will cause the notification migration to fail.\n"
                "We strongly recommend aborting the update and correcting the "
                "invalid configuration first.\n"
            ),
        ],
    )


pre_update_action_registry.register(
    PreMigrateHtmlEmail(
        name="migrate_html_email",
        title="Migrate HTML email",
        sort_index=50,
    )
)
