#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import cast
from uuid import uuid4

from cmk.gui.wato.pages.notifications.quick_setup_types import (
    AlwaysBulk,
    AlwaysBulkTuple,
    AssigneeFilters,
    BulkingParameters,
    ContentBasedFiltering,
    ECAlertFilters,
    FrequencyAndTiming,
    GeneralFilters,
    GeneralProperties,
    HostEvent,
    HostFilters,
    HostIntState,
    Method,
    NotificationMethod,
    NotificationQuickSetupSpec,
    OtherTriggerEvent,
    Receive,
    Recipient,
    RestrictPrevious,
    SendingConditions,
    ServiceEvent,
    ServiceFilters,
    ServiceIntState,
    Settings,
    SpecificEvents,
    StateChangeHost,
    StateChangeService,
    TimeperiodBulk,
    TimeperiodBulkTuple,
    TriggeringEvents,
)
from cmk.utils.notify_types import (
    AlwaysBulkParameters,
    ConditionEventConsoleAlertsType,
    EventRule,
    GroupBy,
    HostEventType,
    is_non_state_change_event_type,
    NonStateChangeEventType,
    NotificationParameterID,
    NotificationRuleID,
    ServiceEventType,
    TimeperiodBulkParameters,
)
from cmk.utils.timeperiod import TimeperiodName


def host_event_mapper(
    host_event_state_change: tuple[HostIntState, HostIntState],
) -> str:
    _state_map: Mapping[HostIntState, str] = {
        -1: "?",
        0: "r",
        1: "d",
        2: "u",
    }
    return "".join([_state_map[state] for state in host_event_state_change])


def service_event_mapper(
    service_event_state_change: tuple[ServiceIntState, ServiceIntState],
) -> str:
    _state_map: Mapping[ServiceIntState, str] = {
        -1: "?",
        0: "r",
        1: "w",
        2: "c",
        3: "u",
    }
    return "".join([_state_map[state] for state in service_event_state_change])


def _get_triggering_events(event_rule: EventRule) -> TriggeringEvents:
    def _non_state_change_events(event: NonStateChangeEventType) -> OtherTriggerEvent:
        state_map: Mapping[NonStateChangeEventType, OtherTriggerEvent] = {
            "f": ("flapping_state", None),
            "s": ("downtime", None),
            "x": ("acknowledgement", None),
            "as": ("alert_handler", "success"),
            "af": ("alert_handler", "failure"),
        }
        return state_map[event]

    def _migrate_host_event(event: HostEventType) -> HostEvent:
        state_map: Mapping[str, HostIntState] = {
            "?": -1,
            "r": 0,
            "d": 1,
            "u": 2,
        }
        state_change_host: StateChangeHost = (
            "state_change",
            (state_map[event[0]], state_map[event[1]]),
        )

        return state_change_host

    def _migrate_service_event(event: ServiceEventType) -> ServiceEvent:
        state_map: Mapping[str, ServiceIntState] = {
            "?": -1,
            "r": 0,
            "w": 1,
            "c": 2,
            "u": 3,
        }
        state_change_service: StateChangeService = (
            "state_change",
            (state_map[event[0]], state_map[event[1]]),
        )
        return state_change_service

    if (
        "match_host_event" not in event_rule
        and "match_service_event" not in event_rule
        and "match_ec" not in event_rule
    ):
        return "all_events", None

    specific_events = SpecificEvents()

    if "match_host_event" in event_rule:
        specific_events["host_events"] = [
            _non_state_change_events(ev)
            if is_non_state_change_event_type(ev)
            else _migrate_host_event(ev)
            for ev in event_rule["match_host_event"]
        ]

    if "match_service_event" in event_rule:
        specific_events["service_events"] = [
            _non_state_change_events(ev)
            if is_non_state_change_event_type(ev)
            else _migrate_service_event(ev)
            for ev in event_rule["match_service_event"]
        ]

    if "match_ec" in event_rule and event_rule["match_ec"] is not False:
        specific_events["ec_alerts"] = True

    return "specific_events", specific_events


def _get_ec_alert_filters(event_rule: EventRule) -> ECAlertFilters:
    ec_alert_filters = ECAlertFilters()
    match_ec = event_rule["match_ec"]
    if not match_ec:
        return ec_alert_filters
    if "match_rule_id" in match_ec:
        ec_alert_filters["rule_ids"] = match_ec["match_rule_id"]
    if "match_priority" in match_ec:
        ec_alert_filters["syslog_priority"] = match_ec["match_priority"]
    if "match_facility" in match_ec:
        ec_alert_filters["syslog_facility"] = match_ec["match_facility"]
    if "match_comment" in match_ec:
        ec_alert_filters["event_comment"] = match_ec["match_comment"]
    return ec_alert_filters


def _get_host_filters(event_rule: EventRule) -> HostFilters:
    host_filters = HostFilters()
    if "match_hosttags" in event_rule:
        host_filters["host_tags"] = event_rule["match_hosttags"]
    if "match_hostlabels" in event_rule:
        host_filters["host_labels"] = event_rule["match_hostlabels"]
    if "match_hostgroups" in event_rule:
        host_filters["match_host_groups"] = event_rule["match_hostgroups"]
    if "match_hosts" in event_rule:
        host_filters["match_hosts"] = event_rule["match_hosts"]
    if "match_exclude_hosts" in event_rule:
        host_filters["exclude_hosts"] = event_rule["match_exclude_hosts"]
    return host_filters


def _get_service_filters(event_rule: EventRule) -> ServiceFilters:
    service_filters = ServiceFilters()
    if "match_servicelabels" in event_rule:
        service_filters["service_labels"] = event_rule["match_servicelabels"]
    if "match_servicegroups" in event_rule:
        service_filters["match_service_groups"] = event_rule["match_servicegroups"]
    if "match_servicegroups_regex" in event_rule:
        service_filters["match_service_groups_regex"] = event_rule["match_servicegroups_regex"]
    if "match_exclude_servicegroups" in event_rule:
        service_filters["exclude_service_groups"] = event_rule["match_exclude_servicegroups"]
    if "match_exclude_servicegroups_regex" in event_rule:
        service_filters["exclude_service_groups_regex"] = event_rule[
            "match_exclude_servicegroups_regex"
        ]
    if "match_services" in event_rule:
        service_filters["match_services"] = event_rule["match_services"]
    if "match_exclude_services" in event_rule:
        service_filters["exclude_services"] = event_rule["match_exclude_services"]
    if "match_checktype" in event_rule:
        service_filters["check_type_plugin"] = event_rule["match_checktype"]
    return service_filters


def _get_assignee_filters(event_rule: EventRule) -> AssigneeFilters:
    assignee_filters = AssigneeFilters()
    if "match_contactgroups" in event_rule:
        assignee_filters["contact_groups"] = event_rule["match_contactgroups"]
    if "match_contacts" in event_rule:
        assignee_filters["users"] = event_rule["match_contacts"]
    return assignee_filters


def _get_general_filters(event_rule: EventRule) -> GeneralFilters:
    general_filters = GeneralFilters()
    if "match_sl" in event_rule:
        if event_rule["match_sl"][0] == event_rule["match_sl"][1]:
            general_filters["service_level"] = ("explicit", event_rule["match_sl"][0])
        else:
            general_filters["service_level"] = ("range", event_rule["match_sl"])
    if "match_folder" in event_rule:
        general_filters["folder"] = event_rule["match_folder"]
    if "match_site" in event_rule:
        general_filters["sites"] = event_rule["match_site"]
    return general_filters


def _get_notification_method(event_rule: EventRule) -> NotificationMethod:
    def _bulk_type() -> AlwaysBulkTuple | TimeperiodBulkTuple | None:
        if (notifybulk := event_rule.get("bulk")) is None:
            return None

        def _get_always_bulk(always_bulk_params: AlwaysBulkParameters) -> AlwaysBulk:
            always_bulk = AlwaysBulk(
                combine=float(always_bulk_params["interval"]),
                bulking_parameters=cast(
                    BulkingParameters,
                    {k: None for k in always_bulk_params["groupby"]},
                ),
                max_notifications=always_bulk_params["count"],
            )
            if custom_macro := always_bulk_params.get("groupby_custom"):
                always_bulk["bulking_parameters"]["custom_macro"] = custom_macro
            if "bulk_subject" in always_bulk_params:
                always_bulk["subject"] = always_bulk_params["bulk_subject"]

            return always_bulk

        def _get_timeperiod_bulk(
            timeperiod_bulk_params: TimeperiodBulkParameters,
        ) -> TimeperiodBulk:
            timeperiod_bulk = TimeperiodBulk(
                bulking_parameters=cast(
                    BulkingParameters,
                    {k: None for k in timeperiod_bulk_params["groupby"]},
                ),
                max_notifications=timeperiod_bulk_params["count"],
            )
            if custom_macro := timeperiod_bulk_params.get("groupby_custom"):
                timeperiod_bulk["bulking_parameters"]["custom_macro"] = custom_macro

            if "bulk_subject" in timeperiod_bulk_params:
                timeperiod_bulk["subject"] = timeperiod_bulk_params["bulk_subject"]

            if "bulk_outside" in timeperiod_bulk_params:
                timeperiod_bulk["bulk_outside_timeperiod"] = _get_always_bulk(
                    timeperiod_bulk_params["bulk_outside"]
                )

            return timeperiod_bulk

        if notifybulk[0] == "always":
            return "always", _get_always_bulk(notifybulk[1])
        return "timeperiod", (
            TimeperiodName(notifybulk[1]["timeperiod"]),
            _get_timeperiod_bulk(notifybulk[1]),
        )

    notify_plugin = event_rule["notify_plugin"]
    if notify_plugin[1] is None:
        return NotificationMethod(notification_effect=("suppress", (notify_plugin[0], None)))
    notify_method = NotificationMethod(
        notification_effect=(
            "send",
            (notify_plugin[0], Method(parameter_id=notify_plugin[1])),
        ),
    )
    if (bulk_notification := _bulk_type()) is not None and notify_method["notification_effect"][
        0
    ] == "send":
        notify_method["notification_effect"][1][1]["bulk_notification"] = bulk_notification

    return notify_method


def _get_recipients(event_rule: EventRule) -> Recipient:
    receivers: list[Receive] = []
    restrict_previous: list[RestrictPrevious] = []
    if event_rule["contact_object"]:
        receivers.append(("all_contacts_affected", None))

    if event_rule["contact_all_with_email"]:
        receivers.append(("all_email_users", None))

    if event_rule["contact_all"]:
        receivers.append(("all_users", None))

    if "contact_groups" in event_rule:
        receivers.append(("contact_group", event_rule["contact_groups"]))

    if "contact_emails" in event_rule:
        receivers.append(("explicit_email_addresses", event_rule["contact_emails"]))

    if "contact_users" in event_rule:
        receivers.append(("specific_users", event_rule["contact_users"]))

    if "contact_match_groups" in event_rule:
        restrict_previous.append(("contact_group", event_rule["contact_match_groups"]))

    if "contact_match_macros" in event_rule:
        restrict_previous.append(("custom_macro", event_rule["contact_match_macros"]))
    recipient = Recipient(receive=receivers)
    if restrict_previous:
        recipient["restrict_previous"] = restrict_previous
    return recipient


def _get_sending_conditions(event_rule: EventRule) -> SendingConditions:
    frequency_and_timing = FrequencyAndTiming()
    if "match_timeperiod" in event_rule:
        frequency_and_timing["restrict_timeperiod"] = event_rule["match_timeperiod"]

    if "match_escalation" in event_rule:
        frequency_and_timing["limit_by_count"] = event_rule["match_escalation"]

    if "match_escalation_throttle" in event_rule:
        frequency_and_timing["throttle_periodic"] = event_rule["match_escalation_throttle"]

    content_based_filtering = ContentBasedFiltering()
    if "match_plugin_output" in event_rule:
        content_based_filtering["by_plugin_output"] = event_rule["match_plugin_output"]

    if "match_notification_comment" in event_rule:
        content_based_filtering["custom_by_comment"] = event_rule["match_notification_comment"]

    return SendingConditions(
        frequency_and_timing=frequency_and_timing,
        content_based_filtering=content_based_filtering,
    )


def _get_general_properties(event_rule: EventRule) -> GeneralProperties:
    settings = Settings()
    if event_rule["disabled"]:
        settings["disable_rule"] = None
    if event_rule["allow_disable"]:
        settings["allow_users_to_disable"] = None

    return GeneralProperties(
        description=event_rule["description"],
        settings=settings,
        comment=event_rule.get("comment", ""),
        documentation_url=event_rule.get("docu_url", ""),
    )


def migrate_to_notification_quick_setup_spec(event_rule: EventRule) -> NotificationQuickSetupSpec:
    spec = NotificationQuickSetupSpec(
        triggering_events=_get_triggering_events(event_rule),
        assignee_filters=_get_assignee_filters(event_rule),
        general_filters=_get_general_filters(event_rule),
        notification_method=_get_notification_method(event_rule),
        recipient=_get_recipients(event_rule),
        sending_conditions=_get_sending_conditions(event_rule),
        general_properties=_get_general_properties(event_rule),
    )
    if "match_ec" in event_rule and event_rule["match_ec"]:
        spec["ec_alert_filters"] = _get_ec_alert_filters(event_rule)
    if any(
        k in event_rule
        for k in [
            "match_hosttags",
            "match_hostlabels",
            "match_hostgroups",
            "match_hosts",
            "match_exclude_hosts",
        ]
    ):
        spec["host_filters"] = _get_host_filters(event_rule)
    if any(
        k in event_rule
        for k in [
            "match_servicelabels",
            "match_servicegroups",
            "match_servicegroups_regex",
            "match_exclude_servicegroups",
            "match_services",
            "match_exclude_services",
            "match_exclude_servicegroups_regex",
        ]
    ):
        spec["service_filters"] = _get_service_filters(event_rule)
    return spec


def _set_triggering_events(event_rule: EventRule, notification: NotificationQuickSetupSpec) -> None:
    def _non_state_change_events(event: OtherTriggerEvent) -> NonStateChangeEventType:
        state_map: Mapping[OtherTriggerEvent, NonStateChangeEventType] = {
            ("flapping_state", None): "f",
            ("downtime", None): "s",
            ("acknowledgement", None): "x",
            ("alert_handler", "success"): "as",
            ("alert_handler", "failure"): "af",
        }
        return state_map[event]

    trigger_events = notification["triggering_events"]
    if trigger_events[0] == "all_events":
        return
    if trigger_events[0] == "specific_events":
        specific_events = trigger_events[1]
        if "host_events" in specific_events:
            event_rule["match_host_event"] = [
                cast(HostEventType, host_event_mapper(ev[1]))
                if ev[0] == "state_change"
                else _non_state_change_events(ev)
                for ev in specific_events["host_events"]
            ]

        if "service_events" in specific_events:
            event_rule["match_service_event"] = [
                cast(ServiceEventType, service_event_mapper(ev[1]))
                if ev[0] == "state_change"
                else _non_state_change_events(ev)
                for ev in specific_events["service_events"]
            ]

        if "ec_alerts" in specific_events and "match_ec" not in event_rule:
            event_rule["match_ec"] = ConditionEventConsoleAlertsType()


def _set_event_console_filters(
    event_rule: EventRule,
    notification: NotificationQuickSetupSpec,
) -> None:
    if (
        notification["triggering_events"][0] == "specific_events"
        and notification["triggering_events"][1].get("ec_alerts") is None
    ):
        return

    if not (ec_alert_filters := notification.get("ec_alert_filters")):
        return

    ec_alerts_type = ConditionEventConsoleAlertsType()
    if "rule_ids" in ec_alert_filters:
        ec_alerts_type["match_rule_id"] = ec_alert_filters["rule_ids"]
    if "syslog_priority" in ec_alert_filters:
        ec_alerts_type["match_priority"] = ec_alert_filters["syslog_priority"]
    if "syslog_facility" in ec_alert_filters:
        ec_alerts_type["match_facility"] = ec_alert_filters["syslog_facility"]
    if "event_comment" in ec_alert_filters:
        ec_alerts_type["match_comment"] = ec_alert_filters["event_comment"]
    if ec_alerts_type:
        event_rule["match_ec"] = ec_alerts_type


def _set_host_filters(event_rule: EventRule, notification: NotificationQuickSetupSpec) -> None:
    if not (host_filters := notification.get("host_filters")):
        return

    if "host_tags" in host_filters:
        event_rule["match_hosttags"] = host_filters["host_tags"]
    if "host_labels" in host_filters:
        event_rule["match_hostlabels"] = host_filters["host_labels"]
    if "match_host_groups" in host_filters:
        event_rule["match_hostgroups"] = host_filters["match_host_groups"]
    if "match_hosts" in host_filters:
        event_rule["match_hosts"] = host_filters["match_hosts"]
    if "exclude_hosts" in host_filters:
        event_rule["match_exclude_hosts"] = host_filters["exclude_hosts"]


def _set_service_filters(event_rule: EventRule, notification: NotificationQuickSetupSpec) -> None:
    if (
        notification["triggering_events"][0] == "specific_events"
        and notification["triggering_events"][1].get("service_events") is None
    ):
        return

    if not (service_filters := notification.get("service_filters")):
        return

    if "service_labels" in service_filters:
        event_rule["match_servicelabels"] = service_filters["service_labels"]
    if "match_service_groups" in service_filters:
        event_rule["match_servicegroups"] = service_filters["match_service_groups"]
    if "match_service_groups_regex" in service_filters:
        event_rule["match_servicegroups_regex"] = service_filters["match_service_groups_regex"]
    if "exclude_service_groups" in service_filters:
        event_rule["match_exclude_servicegroups"] = service_filters["exclude_service_groups"]
    if "exclude_service_groups_regex" in service_filters:
        event_rule["match_exclude_servicegroups_regex"] = service_filters[
            "exclude_service_groups_regex"
        ]
    if "match_services" in service_filters:
        event_rule["match_services"] = service_filters["match_services"]
    if "exclude_services" in service_filters:
        event_rule["match_exclude_services"] = service_filters["exclude_services"]
    if "check_type_plugin" in service_filters:
        event_rule["match_checktype"] = service_filters["check_type_plugin"]


def _set_assignee_filters(event_rule: EventRule, notification: NotificationQuickSetupSpec) -> None:
    assignee_filters = notification["assignee_filters"]
    if "contact_groups" in assignee_filters:
        event_rule["match_contactgroups"] = assignee_filters["contact_groups"]
    if "users" in assignee_filters:
        event_rule["match_contacts"] = assignee_filters["users"]


def _set_general_filters(event_rule: EventRule, notification: NotificationQuickSetupSpec) -> None:
    general_filters = notification["general_filters"]
    if "service_level" in general_filters:
        service_level = general_filters["service_level"]
        match service_level:
            case ("explicit", level):
                assert isinstance(level, int)
                event_rule["match_sl"] = (level, level)
            case ("range", (range_from, range_to)):
                assert isinstance(range_from, int)
                assert isinstance(range_to, int)
                event_rule["match_sl"] = (range_from, range_to)
    if "folder" in general_filters:
        event_rule["match_folder"] = general_filters["folder"]
    if "sites" in general_filters:
        event_rule["match_site"] = general_filters["sites"]


def _set_notification_effect_parameters(
    event_rule: EventRule, notification: NotificationQuickSetupSpec
) -> None:
    def _get_always_bulk_parameters(
        always_bulk: AlwaysBulk,
    ) -> AlwaysBulkParameters:
        always_bulk_params = AlwaysBulkParameters(
            interval=int(always_bulk["combine"]),
            count=always_bulk["max_notifications"],
            groupby=cast(
                list[GroupBy],
                [k for k in always_bulk["bulking_parameters"] if k != "custom_macro"],
            ),
        )
        if custom_macro := always_bulk["bulking_parameters"].get("custom_macro"):
            always_bulk_params["groupby_custom"] = custom_macro
        if "subject" in always_bulk:
            always_bulk_params["bulk_subject"] = always_bulk["subject"]
        return always_bulk_params

    def _get_timeperiod_bulk_parameters(
        timeperiod: TimeperiodName, time_period_bulk: TimeperiodBulk
    ) -> TimeperiodBulkParameters:
        time_period_bulk_params = TimeperiodBulkParameters(
            timeperiod=timeperiod,
            count=time_period_bulk["max_notifications"],
            groupby=cast(
                list[GroupBy],
                [k for k in time_period_bulk["bulking_parameters"] if k != "custom_macro"],
            ),
        )

        if custom_macro := time_period_bulk["bulking_parameters"].get("custom_macro"):
            time_period_bulk_params["groupby_custom"] = custom_macro

        if "subject" in time_period_bulk:
            time_period_bulk_params["bulk_subject"] = time_period_bulk["subject"]

        if "bulk_outside_timeperiod" in time_period_bulk:
            time_period_bulk_params["bulk_outside"] = _get_always_bulk_parameters(
                time_period_bulk["bulk_outside_timeperiod"],
            )
        return time_period_bulk_params

    notification_effect = notification["notification_method"]["notification_effect"]
    if notification_effect[0] == "suppress":
        event_rule["notify_plugin"] = notification_effect[1]
        return

    if notification_effect[0] == "send":
        event_rule["notify_plugin"] = (
            notification_effect[1][0],
            notification_effect[1][1]["parameter_id"],
        )

    if (bulk_notification := notification_effect[1][1].get("bulk_notification")) is not None:
        if bulk_notification[0] == "always":
            event_rule["bulk"] = (
                bulk_notification[0],
                _get_always_bulk_parameters(bulk_notification[1]),
            )
        else:
            event_rule["bulk"] = (
                bulk_notification[0],
                _get_timeperiod_bulk_parameters(bulk_notification[1][0], bulk_notification[1][1]),
            )


def _set_recipients(event_rule: EventRule, notification: NotificationQuickSetupSpec) -> None:
    for recipient in notification["recipient"]["receive"]:
        match recipient:
            case ("all_contacts_affected", None):
                event_rule["contact_object"] = True

            case ("all_email_users", None):
                event_rule["contact_all_with_email"] = True

            case ("contact_group", list() as contact_groups):
                event_rule["contact_groups"] = contact_groups

            case ("explicit_email_addresses", list() as emails):
                event_rule["contact_emails"] = emails

            case ("specific_users", list() as users):
                event_rule["contact_users"] = users

            case ("all_users", None):
                event_rule["contact_all"] = True

            case _:
                raise ValueError(f"Invalid recipient: {recipient}")

    for restriction in notification["recipient"].get("restrict_previous", []):
        match restriction:
            case ("contact_group", list() as r_contact_groups):
                event_rule["contact_match_groups"] = r_contact_groups

            case ("custom_macro", list() as custom_macros):
                event_rule["contact_match_macros"] = custom_macros

            case _:
                raise ValueError(f"Invalid restriction: {restriction}")


def _set_sending_conditions(
    event_rule: EventRule, notification: NotificationQuickSetupSpec
) -> None:
    frequency_and_timing = notification["sending_conditions"]["frequency_and_timing"]
    if "restrict_timeperiod" in frequency_and_timing:
        event_rule["match_timeperiod"] = frequency_and_timing["restrict_timeperiod"]
    if "limit_by_count" in frequency_and_timing:
        event_rule["match_escalation"] = frequency_and_timing["limit_by_count"]
    if "throttle_periodic" in frequency_and_timing:
        event_rule["match_escalation_throttle"] = frequency_and_timing["throttle_periodic"]
    content_based_filtering = notification["sending_conditions"]["content_based_filtering"]
    if "by_plugin_output" in content_based_filtering:
        event_rule["match_plugin_output"] = content_based_filtering["by_plugin_output"]
    if "custom_by_comment" in content_based_filtering:
        event_rule["match_notification_comment"] = content_based_filtering["custom_by_comment"]


def _set_general_properties(
    event_rule: EventRule, notification: NotificationQuickSetupSpec
) -> None:
    if "disable_rule" in notification["general_properties"]["settings"]:
        event_rule["disabled"] = True

    if "allow_users_to_disable" in notification["general_properties"]["settings"]:
        event_rule["allow_disable"] = True

    if "comment" in notification["general_properties"]:
        event_rule["comment"] = notification["general_properties"]["comment"]

    if "documentation_url" in notification["general_properties"]:
        event_rule["docu_url"] = notification["general_properties"]["documentation_url"]

    event_rule["description"] = notification["general_properties"]["description"]


def migrate_to_event_rule(notification: NotificationQuickSetupSpec) -> EventRule:
    event_rule = EventRule(
        rule_id=NotificationRuleID(str(uuid4())),
        allow_disable=False,
        contact_all=False,
        contact_all_with_email=False,
        contact_object=False,
        description="foo",
        disabled=False,
        notify_plugin=("mail", NotificationParameterID("parameter_id")),
    )

    _set_event_console_filters(event_rule, notification)
    _set_host_filters(event_rule, notification)
    _set_service_filters(event_rule, notification)
    _set_assignee_filters(event_rule, notification)
    _set_general_filters(event_rule, notification)
    _set_triggering_events(event_rule, notification)
    _set_notification_effect_parameters(event_rule, notification)
    _set_recipients(event_rule, notification)
    _set_sending_conditions(event_rule, notification)
    _set_general_properties(event_rule, notification)

    return event_rule
