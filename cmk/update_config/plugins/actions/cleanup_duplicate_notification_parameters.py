#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.gui.watolib.notifications import (
    make_parameter_hashable,
    NotificationParameterConfigFile,
    NotificationRuleConfigFile,
)

from cmk.update_config.registry import update_action_registry, UpdateAction


class CleanupDuplicateNotificationParameters(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        notification_rules = NotificationRuleConfigFile().load_for_modification()
        notification_parameters = NotificationParameterConfigFile().load_for_modification()

        hashed_params_map = {}
        params_id_map = {}

        logger.debug("Removing duplicate notification parameters.")
        for method, params in notification_parameters.items():
            method_params = {}
            for paramid, param in params.items():
                hashed_dict = hash(make_parameter_hashable(param))
                if hashed_dict not in hashed_params_map:
                    method_params[paramid] = param
                    hashed_params_map[hashed_dict] = paramid
                else:
                    params_id_map[paramid] = hashed_params_map[hashed_dict]

            notification_parameters[method] = method_params

        logger.debug("Update rules to point to the correct parameter set.")
        for notification_rule in notification_rules:
            notify_method, notify_param_id = notification_rule["notify_plugin"]
            if notify_param_id is None:
                continue

            if notification_parameters.get(notify_method, {}).get(notify_param_id):
                continue

            notification_rule["notify_plugin"] = (
                (notify_method, params_id_map[notify_param_id])
                if notify_param_id in params_id_map
                else (notify_method, None)
            )

        logger.debug("Saving updated notification parameters.")
        NotificationParameterConfigFile().save(notification_parameters)

        logger.debug("Saving updated notification rules.")
        NotificationRuleConfigFile().save(notification_rules)


update_action_registry.register(
    CleanupDuplicateNotificationParameters(
        name="cleanup_duplicate_notification_parameters",
        title="Cleanup duplicate notification parameters",
        sort_index=51,  # has to run after migrate_notifications.py
    )
)
