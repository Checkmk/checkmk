#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, NotRequired, TypedDict

StatusChangeStateHost = Literal[-1, 0, 1, 2]
StatusChangeStateService = Literal[-1, 0, 1, 2, 3]
StatusChangeHost = tuple[
    Literal["status_change"], tuple[StatusChangeStateHost, StatusChangeStateHost]
]
StatusChangeService = tuple[
    Literal["status_change"], tuple[StatusChangeStateService, StatusChangeStateService]
]
Downtime = tuple[Literal["downtime"], None]
Acknowledgement = tuple[Literal["acknowledgement"], None]
FlappingState = tuple[Literal["flapping_state"], None]
AlertHandler = tuple[Literal["alert_handler"], Literal["success", "failure"]]
OtherTriggerEvent = Downtime | Acknowledgement | FlappingState | AlertHandler

HostEvent = StatusChangeHost | OtherTriggerEvent
ServiceEvent = StatusChangeService | OtherTriggerEvent


class TriggeringEvents(TypedDict):
    host_events: NotRequired[list[HostEvent]]
    service_events: NotRequired[list[ServiceEvent]]
    ec_alerts: NotRequired[Literal["Enabled"]]


# TODO: add correct types after Stage 2 is implemented
class FilterForHostsAndServices(TypedDict):
    ec_alert_filters: object
    host_filters: object
    service_filters: object
    assignee_filters: object
    general_filters: object


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
    bulking_outside_timeperiod: NotRequired[AlwaysBulk]


AlwaysBulkTuple = tuple[Literal["always"], AlwaysBulk]
TimeperiodBulkTuple = tuple[Literal["timeperiod"], tuple[str, TimeperiodBulk]]
BulkNotificatons = AlwaysBulkTuple | TimeperiodBulkTuple


class Effect(TypedDict):
    method: tuple[str, str]
    bulk_notification: NotRequired[BulkNotificatons]


NotificationEffect = tuple[Literal["send", "suppress"], Effect]


class NotificationMethod(TypedDict):
    notification_effect: NotificationEffect


AllContactsAffected = tuple[Literal["all_contacts_affected"], None]
AllEmailUsers = tuple[Literal["all_email_users"], None]
ContactGroup = tuple[Literal["contact_group"], list[str]]
ExplicitEmail = tuple[Literal["explicit_email_addresses"], list[str]]
CustomMacro = tuple[Literal["custom_macro"], list[tuple[str, str]]]
RestrictPrevious = tuple[Literal["restrict_previous"], ContactGroup | CustomMacro]
SpecificUsers = tuple[Literal["specific_users"], list[str]]
AllUsers = tuple[Literal["all_users"], None]

Recipient = (
    AllContactsAffected
    | AllEmailUsers
    | ContactGroup
    | ExplicitEmail
    | RestrictPrevious
    | SpecificUsers
    | AllUsers
)


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
    filter_for_hosts_and_services: FilterForHostsAndServices
    notification_method: NotificationMethod
    recipient: list[Recipient]
    sending_conditions: SendingConditions
    general_properties: GeneralProperties
