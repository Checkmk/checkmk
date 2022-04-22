#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict, Union

from ._misc import TimeperiodName

ContactName = str

HandlerName = str
HandlerParameters = dict[str, Any]

NotifyPluginParamsList = List[str]
NotifyPluginParamsDict = Dict[str, Any]  # TODO: Improve this
NotifyPluginParams = Union[NotifyPluginParamsList, NotifyPluginParamsDict]
NotifyBulkParameters = Dict[str, Any]  # TODO: Improve this
NotificationType = Literal[
    "ACKNOWLEDGEMENT",
    "DOWNTIMECANCELLED",
    "DOWNTIMEEND",
    "DOWNTIMESTART",
    "FLAPPINGDISABLED",
    "FLAPPINGSTART",
    "FLAPPINGSTOP",
    "PROBLEM",
    "RECOVERY",
]


class EventRule(TypedDict, total=False):
    """Event Rule

    used to be Dict[str, Any], feel free to add stuff"""

    alert_handler: tuple[HandlerName, HandlerParameters]
    allow_disable: bool
    contact: str
    contact_all: bool
    contact_all_with_email: bool
    contact_emails: list[str]
    contact_groups: list[str]
    contact_match_groups: list[str]
    contact_match_macros: list[tuple[str, str]]
    contact_object: bool
    contact_users: list[str]
    description: str
    disabled: bool
    match_attempt: tuple[int, int]
    match_checktype: list[str]
    match_contactgroups: list[str]
    match_contacts: list[str]
    match_ec: Union[Literal[False], dict[str, Any]]  # cmk/gui/wato/pages/notifications.py
    match_escalation: tuple[int, int]
    match_escalation_throttle: tuple[int, int]
    match_exclude_hosts: list[str]
    match_exclude_servicegroups: str
    match_exclude_servicegroups_regex: tuple[None, None]
    match_exclude_services: list[str]
    match_folder: str
    match_host_event: list[str]
    match_hostgroups: list[str]
    match_hostlabels: dict[str, str]
    match_hosts: list[str]
    match_hosttags: list[str]
    match_notification_comment: str
    match_plugin_output: str
    match_service_event: list[str]
    match_servicegroups: str
    match_servicegroups_regex: tuple[None, None]
    match_servicelabels: dict[str, str]
    match_services: list[str]
    match_site: list[str]
    match_sl: tuple[int, int]
    match_timeperiod: TimeperiodName
    notify_method: NotifyPluginParams
    notify_plugin: tuple[str, NotifyPluginParams]
    # tuple is the "new" way but we still have compatable code
    bulk: Union[tuple[Literal["always", "timeperiod"], NotifyBulkParameters], NotifyBulkParameters]


NotifyRuleInfo = Tuple[str, EventRule, str]
NotifyPluginName = str
NotifyPluginInfo = Tuple[
    ContactName, NotifyPluginName, NotifyPluginParams, Optional[NotifyBulkParameters]
]
NotifyAnalysisInfo = Tuple[List[NotifyRuleInfo], List[NotifyPluginInfo]]

UUIDs = List[Tuple[float, str]]
NotifyBulk = Tuple[str, float, Union[None, str, int], Union[None, str, int], int, UUIDs]
NotifyBulks = List[NotifyBulk]


class DisabledNotificationsOptions(TypedDict, total=False):
    disabled: bool
    timerange: tuple[float, float]


class Contact(TypedDict, total=False):
    alias: str
    contactgroups: Union[tuple[str, ...], list[str]]
    disable_notifications: DisabledNotificationsOptions
    email: str
    name: str
    pager: str


class EventContext(TypedDict, total=False):
    """Used to be Dict[str, Any]"""

    CONTACTNAME: str
    CONTACTS: str
    DATE: str
    EC_COMMENT: str
    EC_FACILITY: str
    EC_PRIORITY: str
    EC_RULE_ID: str
    HOSTATTEMPT: str
    HOSTCONTACTGROUPNAMES: str
    HOSTFORURL: str
    HOSTGROUPNAMES: str
    HOSTNAME: str
    HOSTNOTIFICATIONNUMBER: str
    HOSTOUTPUT: str
    HOSTSTATE: Literal["UP", "DOWN", "UNREACHABLE"]
    HOSTTAGS: str
    HOSTURL: str
    HOST_SL: str
    LASTHOSTSTATE: str
    LASTHOSTSTATECHANGE: str
    LASTHOSTSTATECHANGE_REL: str
    LASTHOSTUP: str
    LASTHOSTUP_REL: str
    LASTSERVICEOK: str
    LASTSERVICEOK_REL: str
    LASTSERVICESTATE: str
    LASTSERVICESTATECHANGE: str
    LASTSERVICESTATECHANGE_REL: str
    LOGDIR: str
    LONGDATETIME: str
    LONGSERVICEOUTPUT: str
    MICROTIME: str
    MONITORING_HOST: str
    NOTIFICATIONCOMMENT: str
    NOTIFICATIONTYPE: NotificationType
    OMD_ROOT: str
    OMD_SITE: str
    PREVIOUSHOSTHARDSTATE: str
    PREVIOUSSERVICEHARDSTATE: str
    SERVICEATTEMPT: str
    SERVICECHECKCOMMAND: str
    SERVICECONTACTGROUPNAMES: str
    SERVICEDESC: str
    SERVICEFORURL: str
    SERVICEGROUPNAMES: str
    SERVICENOTIFICATIONNUMBER: str
    SERVICEOUTPUT: str
    SERVICESTATE: str
    SERVICEURL: str
    SHORTDATETIME: str
    SVC_SL: str
    WHAT: Literal["SERVICE", "HOST"]

    # Dynamically added:
    # HOSTLABEL_*: str
    # SERVICELABEL_*: str

    # Dynamically added:
    # # Add short variants for state names (at most 4 characters)
    # for key, value in list(raw_context.items()):
    #     if key.endswith("STATE"):
    #         raw_context[key[:-5] + "SHORTSTATE"] = value[:4]
    # We know of:
    HOSTSHORTSTATE: str
    LASTHOSTSHORTSTATE: str
    LASTSERVICESHORTSTATE: str
    PREVIOUSHOSTHARDSHORTSTATE: str
    PREVIOUSSERVICEHARDSHORTSTATE: str
    SERVICESHORTSTATE: str


class ECEventContext(EventContext, total=False):
    """The keys "found" in cmk.ec

    Not sure if subclassing EventContext is the right call...
    Feel free to merge if you feel like doing it.
    """

    EC_CONTACT: str
    EC_CONTACT_GROUPS: str
    EC_ID: str
    EC_MATCH_GROUPS: str
    EC_ORIG_HOST: str
    EC_OWNER: str
    EC_PHASE: str
    EC_PID: str
    HOSTADDRESS: str
    HOSTALIAS: str
    HOSTDOWNTIME: str
    LASTSERVICESTATEID: str
    NOTIFICATIONAUTHOR: str
    NOTIFICATIONAUTHORALIAS: str
    NOTIFICATIONAUTHORNAME: str
    SERVICEACKAUTHOR: str
    SERVICEACKCOMMENT: str
    SERVICEPERFDATA: str
    SERVICEPROBLEMID: str
    SERVICESTATEID: str
    SERVICE_EC_CONTACT: str
    SERVICE_SL: str

    # Dynamically added:
    # HOST_*: str  #  custom_variables
