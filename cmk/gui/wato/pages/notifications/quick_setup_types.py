#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Literal, NotRequired, TypedDict

from cmk.utils.notify_types import (
    NotificationParameterID,
    NotificationPluginNameStr,
    SysLogFacilityIntType,
    SyslogPriorityIntType,
)
from cmk.utils.rulesets.ruleset_matcher import TagCondition
from cmk.utils.tags import TagGroupID

HostIntState = Literal[-1, 0, 1, 2]
ServiceIntState = Literal[-1, 0, 1, 2, 3]
StateChangeHost = tuple[Literal["state_change"], tuple[HostIntState, HostIntState]]
StateChangeService = tuple[Literal["state_change"], tuple[ServiceIntState, ServiceIntState]]
Downtime = tuple[Literal["downtime"], None]
Acknowledgement = tuple[Literal["acknowledgement"], None]
FlappingState = tuple[Literal["flapping_state"], None]
AlertHandler = tuple[Literal["alert_handler"], Literal["success", "failure"]]
OtherTriggerEvent = Downtime | Acknowledgement | FlappingState | AlertHandler

HostEvent = StateChangeHost | OtherTriggerEvent
ServiceEvent = StateChangeService | OtherTriggerEvent


class SpecificEvents(TypedDict):
    host_events: NotRequired[list[HostEvent]]
    service_events: NotRequired[list[ServiceEvent]]
    ec_alerts: NotRequired[Literal[True]]


TriggeringEvents = (
    tuple[Literal["specific_events"], SpecificEvents] | tuple[Literal["all_events"], None]
)


class ECAlertFilters(TypedDict):
    rule_ids: NotRequired[list[str]]
    syslog_priority: NotRequired[tuple[SyslogPriorityIntType, SyslogPriorityIntType]]
    syslog_facility: NotRequired[SysLogFacilityIntType]
    event_comment: NotRequired[str]


class HostFilters(TypedDict):
    host_tags: NotRequired[
        Mapping[TagGroupID, TagCondition]
    ]  # TODO: double check this type after implementation
    host_labels: NotRequired[dict[str, str]]  # TODO: double check this type after implementation
    match_host_groups: NotRequired[list[str]]
    match_hosts: NotRequired[list[str]]
    exclude_hosts: NotRequired[list[str]]


class ServiceFilters(TypedDict):
    service_labels: NotRequired[dict[str, str]]  # TODO: double check this type after implementation
    match_service_groups: NotRequired[list[str]]
    exclude_service_groups: NotRequired[list[str]]
    match_services: NotRequired[list[str]]
    exclude_services: NotRequired[list[str]]


class AssigneeFilters(TypedDict):
    contact_groups: NotRequired[list[str]]
    users: NotRequired[list[str]]


class GeneralFilters(TypedDict):
    service_level: NotRequired[
        tuple[Literal["explicit"], int] | tuple[Literal["range"], tuple[int, int]]
    ]
    folder: NotRequired[str]
    sites: NotRequired[list[str]]
    check_type_plugin: NotRequired[list[str]]


class BulkingParameters(TypedDict):
    check_type: NotRequired[None]
    custom_macro: NotRequired[list[str]]
    ec_comment: NotRequired[None]
    ec_contact: NotRequired[None]
    folder: NotRequired[None]
    host: NotRequired[None]
    state: NotRequired[None]
    service: NotRequired[None]
    sl: NotRequired[None]


class CommonBulk(TypedDict):
    bulking_parameters: BulkingParameters
    max_notifications: int
    subject: NotRequired[str]


class AlwaysBulk(CommonBulk):
    combine: float


class TimeperiodBulk(CommonBulk):
    bulk_outside_timeperiod: NotRequired[AlwaysBulk]


AlwaysBulkTuple = tuple[Literal["always"], AlwaysBulk]
TimeperiodBulkTuple = tuple[Literal["timeperiod"], tuple[str, TimeperiodBulk]]
BulkNotificatons = AlwaysBulkTuple | TimeperiodBulkTuple


class Method(TypedDict):
    parameter_id: NotificationParameterID
    bulk_notification: NotRequired[BulkNotificatons]


NotificationEffect = (
    tuple[Literal["send"], tuple[NotificationPluginNameStr, Method]]
    | tuple[Literal["suppress"], tuple[NotificationPluginNameStr, None]]
)


class NotificationMethod(TypedDict):
    notification_effect: NotificationEffect


AllContactsAffected = tuple[Literal["all_contacts_affected"], None]
AllEmailUsers = tuple[Literal["all_email_users"], None]
ContactGroup = tuple[Literal["contact_group"], list[str]]
ExplicitEmail = tuple[Literal["explicit_email_addresses"], list[str]]
CustomMacro = tuple[Literal["custom_macro"], list[tuple[str, str]]]
SpecificUsers = tuple[Literal["specific_users"], list[str]]
AllUsers = tuple[Literal["all_users"], None]


RestrictPrevious = ContactGroup | CustomMacro
Receive = (
    AllContactsAffected | AllEmailUsers | ContactGroup | ExplicitEmail | SpecificUsers | AllUsers
)


class Recipient(TypedDict):
    receive: list[Receive]
    restrict_previous: NotRequired[list[RestrictPrevious]]


class FrequencyAndTiming(TypedDict):
    restrict_timeperiod: NotRequired[str]
    limit_by_count: NotRequired[tuple[int, int]]
    throttle_periodic: NotRequired[tuple[int, int]]


class ContentBasedFiltering(TypedDict):
    by_plugin_output: NotRequired[str]
    custom_by_comment: NotRequired[str]


class SendingConditions(TypedDict):
    frequency_and_timing: FrequencyAndTiming
    content_based_filtering: ContentBasedFiltering


class Settings(TypedDict):
    disable_rule: NotRequired[None]
    allow_users_to_disable: NotRequired[None]


class GeneralProperties(TypedDict):
    description: str
    settings: Settings
    comment: str
    documentation_url: str


class NotificationQuickSetupSpec(TypedDict):
    triggering_events: TriggeringEvents
    ec_alert_filters: NotRequired[ECAlertFilters]
    host_filters: NotRequired[HostFilters]
    service_filters: NotRequired[ServiceFilters]
    assignee_filters: AssigneeFilters
    general_filters: GeneralFilters
    notification_method: NotificationMethod
    recipient: Recipient
    sending_conditions: SendingConditions
    general_properties: GeneralProperties
