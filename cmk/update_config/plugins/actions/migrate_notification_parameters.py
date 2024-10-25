#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import cast

from cmk.utils.notify_types import (
    NotificationParameterGeneralInfos,
    NotificationParameterItem,
    NotificationParameterMethod,
    NotificationParameterSpecs,
)

from cmk.gui.watolib import sample_config
from cmk.gui.watolib.notifications import (
    NotificationParameterConfigFile,
    NotificationRuleConfigFile,
)

from cmk.update_config.registry import update_action_registry, UpdateAction


class MigrateNotificationParameters(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        parameters_per_method: NotificationParameterSpecs = {}
        for nr, rule in enumerate(NotificationRuleConfigFile().load_for_reading()):
            method, parameter = rule["notify_plugin"]

            # skip "Call with the following parameters" for now
            if isinstance(parameter, list):
                continue

            parameters_per_method.setdefault(
                NotificationParameterMethod(method),
                {},
            )

            if any(
                parameter == params["parameter_properties"]
                for _parameter_id, params in parameters_per_method[method].items()
            ):
                continue

            parameters_per_method[method].update(
                {
                    sample_config.new_notification_parameter_id(): NotificationParameterItem(
                        general=NotificationParameterGeneralInfos(
                            description="Migrated from notification rule #%d" % nr,
                            comment="Auto migrated on update",
                            docu_url="",
                        ),
                        parameter_properties=cast(dict, parameter),
                    )
                }
            )

        NotificationParameterConfigFile().save(parameters_per_method)


update_action_registry.register(
    MigrateNotificationParameters(
        name="migrate_notification_parameters",
        title="Migrate notification parameters",
        sort_index=50,
    )
)
