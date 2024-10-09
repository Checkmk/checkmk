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

HostEvents = StatusChangeHost | Downtime | Acknowledgement | FlappingState | AlertHandler
ServiceEvents = StatusChangeService | Downtime | Acknowledgement | FlappingState | AlertHandler


class TriggeringEvents(TypedDict):
    host_events: list[HostEvents]
    service_events: list[ServiceEvents]
    ec_alerts: NotRequired[Literal["Enabled"]]


# TODO: add correct types after Stage 2 is implemented
class FilterForHostsAndServices(TypedDict):
    host_filters: object
    service_filters: object
    assignee_filters: object
    general_filters: object


# TODO: add correct types after Stage 3 is implemented
class NotificationMethod(TypedDict):
    effect: object
    method: object
    bulk_notification: NotRequired[object]


AllContactsAffected = tuple[Literal["all_contacts_affected"], None]
AllEmailUsers = tuple[Literal["all_email_users"], None]
ContactGroup = tuple[Literal["contact_group"], str]
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
    | CustomMacro
    | RestrictPrevious
    | SpecificUsers
    | AllUsers
)


# TODO: add correct types after Stage 5 is implemented
class SendingConditions(TypedDict):
    restrict_to_timeperiod: object
    limit_by_count: object
    throttling_of_period: object
    by_plugin_output: object
    custom_by_comment: object


class Settings(TypedDict):
    disable_rule: NotRequired[None]
    allow_users_to_disable: NotRequired[None]


class GeneralProperties(TypedDict):
    description: str
    settings: Settings
    comment: str
    documentation: str


class NotificationQuickSetupSpec(TypedDict):
    triggering_events: TriggeringEvents
    filter_for_hosts_and_services: FilterForHostsAndServices
    notification_method: NotificationMethod
    recipient: list[Recipient]
    sending_conditions: SendingConditions
    general_properties: GeneralProperties
