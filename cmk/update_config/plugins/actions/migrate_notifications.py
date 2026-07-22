#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import Any, cast

from cmk.utils import tty
from cmk.utils.notify_types import (
    ConditionEventConsoleAlertsType,
    EventRule,
    HostEventType,
    NotificationParameterGeneralInfos,
    NotificationParameterID,
    NotificationParameterItem,
    NotificationParameterMethod,
    NotificationParameterSpecs,
    ServiceEventType,
)
from cmk.utils.paths import check_mk_config_dir, omd_root

from cmk.gui.form_specs.vue.form_spec_visitor import process_validation_messages
from cmk.gui.form_specs.vue.visitors import (
    DataOrigin,
    get_visitor,
    VisitorOptions,
)
from cmk.gui.form_specs.vue.visitors._type_defs import DiskModel
from cmk.gui.watolib import sample_config
from cmk.gui.watolib.notification_parameter import notification_parameter_registry
from cmk.gui.watolib.notifications import (
    NotificationParameterConfigFile,
    NotificationRuleConfigFile,
)

from cmk.update_config.registry import update_action_registry, UpdateAction

# We're dealing with both the legacy and migrated representation of the "notify_plugin" parameter
# field. So, we need a type to account for both regresentations.
type LegacyParameter = dict[str, object] | list[object]
type MigratedParameter = NotificationParameterID | None
type Parameter = LegacyParameter | MigratedParameter

# Complete set of host/service notification event types (see _get_host_event_choices and
# _get_service_event_choices in cmk/gui/wato/pages/events.py). The "?x" wildcards match any
# preceding state, so together with the non-state-change events they cover every notification
# a rule can receive.
_ALL_HOST_EVENTS: list[HostEventType] = ["?r", "?d", "?u", "f", "s", "x", "as", "af"]
_ALL_SERVICE_EVENTS: list[ServiceEventType] = ["?r", "?w", "?c", "?u", "f", "s", "x", "as", "af"]


class MigrateNotifications(UpdateAction):
    def __init__(self, name: str, title: str, sort_index: int) -> None:
        super().__init__(name=name, title=title, sort_index=sort_index)
        self._notifications_mk_path: Path = Path(check_mk_config_dir, "wato/notifications.mk")
        self._notifications_mk_backup_path: Path = omd_root / "notifications_backup.mk"

    def __call__(self, logger: Logger) -> None:
        notification_rules = NotificationRuleConfigFile().load_for_reading()
        notification_rule_params = (rule["notify_plugin"][1] for rule in notification_rules)
        if all(params is None or isinstance(params, str) for params in notification_rule_params):
            logger.debug("       Already migrated")
            return

        logger.debug("       Start backup of existing notification configuration.")
        self._backup_notification_config(logger)
        logger.debug("       Finished backup of existing notification configuration.")

        parameters_per_method: NotificationParameterSpecs = {}
        updated_notification_rules: list[EventRule] = []
        for nr, rule in enumerate(notification_rules):
            self._preserve_pre_24_ec_alert_matching(rule)

            method = rule["notify_plugin"][0]
            parameter = cast(Parameter, rule["notify_plugin"][1])

            if parameter is None or isinstance(parameter, str):
                rule["notify_plugin"] = (method, parameter)
                updated_notification_rules.append(rule)
                continue

            parameters_per_method.setdefault(method, {})

            parameter_id = next(
                (
                    param_id
                    for param_id, params in parameters_per_method[method].items()
                    if params["parameter_properties"] == parameter
                ),
                None,
            )

            if parameter_id is None:
                # Special handling for custom plugins whose parameter values may be a list.
                if isinstance(parameter, list):
                    parameter = {"params": parameter}

                parameter_id = sample_config.new_notification_parameter_id()
                data_for_disk = self._get_data_for_disk(method=method, parameter=parameter, nr=nr)
                parameters_per_method[method].update({parameter_id: data_for_disk})

            else:
                description = (
                    parameters_per_method[method][parameter_id]["general"]["description"].replace(
                        "rule", "rules"
                    )
                    + f", #{nr}"
                )
                parameters_per_method[method][parameter_id]["general"]["description"] = description

            rule["notify_plugin"] = (method, parameter_id)
            updated_notification_rules.append(rule)

        NotificationParameterConfigFile().save(parameters_per_method)
        logger.debug("       Saved migrated notification parameters")

        NotificationRuleConfigFile().save(updated_notification_rules)
        logger.debug("       Saved migrated notification rules")

    @staticmethod
    def _preserve_pre_24_ec_alert_matching(rule: EventRule) -> None:
        """Keep pre-2.4 Event Console alert matching for rules migrated from 2.3.

        Event Console alerts are service notifications, so before 2.4 a rule
        matching service events (without ``match_ec``) also matched them. Werk
        #18082 changed this; add an empty ``match_ec`` to keep them matching (the
        service event filter still applies). Host-event-only rules already excluded
        EC alerts and are left untouched.

        The legacy ``match_ec=False`` ("Do not match Event Console alerts") has no
        2.4 equivalent and is dropped. When the rule also restricts host or service
        events, dropping it keeps Event Console alerts excluded as before (and avoids
        the broken 2.4 matching of a stored ``False``). But a rule with
        ``match_ec=False`` and no event restriction matched *all* host and service
        notifications except Event Console alerts; simply dropping the key would turn
        it into an "all events" rule that suddenly also matches Event Console alerts.
        To preserve the original behaviour we make the "all host and service events"
        selection explicit before dropping ``match_ec``.
        """
        if "match_ec" in rule:
            if rule["match_ec"] is False:
                if "match_host_event" not in rule and "match_service_event" not in rule:
                    rule["match_host_event"] = list(_ALL_HOST_EVENTS)
                    rule["match_service_event"] = list(_ALL_SERVICE_EVENTS)
                del rule["match_ec"]
            return
        if "match_service_event" in rule:
            rule["match_ec"] = ConditionEventConsoleAlertsType()

    def _backup_notification_config(self, logger: Logger) -> None:
        self._notifications_mk_backup_path.write_text(self._notifications_mk_path.read_text())
        logger.info(
            f"{tty.yellow}       Wrote notification configuration backup to\n"
            f"       {str(self._notifications_mk_backup_path)}.\n\n"
            "       Please check if the notification pages in the GUI work as "
            "expected.\n       In case of problems you can copy the backup "
            "files back to \n"
            f"       {str(self._notifications_mk_path)}.\n"
            "       If everything works as expected you can remove the backup.\n"
        )

    def _get_data_for_disk(
        self,
        method: NotificationParameterMethod,
        parameter: dict[str, Any],
        nr: int,
    ) -> DiskModel:
        data = NotificationParameterItem(
            general=NotificationParameterGeneralInfos(
                description="Migrated from notification rule #%d" % nr,
                comment="Auto migrated on update",
                docu_url="",
            ),
            parameter_properties={"method_parameters": parameter},
        )
        form_spec = notification_parameter_registry.form_spec(method)
        visitor = get_visitor(form_spec, VisitorOptions(DataOrigin.DISK))

        validation_errors = visitor.validate(data)
        process_validation_messages(validation_errors)

        return visitor.to_disk(data)


update_action_registry.register(
    MigrateNotifications(
        name="migrate_notifications",
        title="Migrate notifications",
        sort_index=50,
    )
)
